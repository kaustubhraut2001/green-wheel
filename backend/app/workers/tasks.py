"""
Celery tasks.

All tasks use:
- autoretry_for: automatically retry on specified exceptions
- max_retries: cap retries to avoid infinite loops
- countdown / exponential backoff: avoid thundering herd on recovery
- bind=True: gives access to self (task instance) for retry control

Dead Letter Queue strategy:
When max_retries is exhausted, Celery raises MaxRetriesExceededError.
We catch it and push the task to the dead_letter queue where an ops team
can inspect and replay it safely after the root cause is fixed.
"""
import asyncio
import logging
from typing import Optional

import structlog
from celery import Task
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.refresh_exchange_rates_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,         # exponential backoff: 60s, 120s, 240s
    retry_backoff_max=600,      # cap at 10 minutes
    retry_jitter=True,          # add randomness to avoid thundering herd
)
def refresh_exchange_rates_task(self):
    """
    Scheduled task: refresh all exchange rates from the configured provider.
    Runs every hour via Celery Beat.
    On failure: retries with exponential backoff up to 3 times.
    On exhaustion: task is acknowledged as failed (logged for DLQ review).
    """
    try:
        logger.info("exchange_rate_refresh_started")

        async def _run():
            from sqlalchemy.ext.asyncio import AsyncSession
            from app.db.session import AsyncSessionLocal
            from app.services.exchange_rate_service import ExchangeRateService

            async with AsyncSessionLocal() as db:
                service = ExchangeRateService(db)
                return await service.refresh_all_rates()

        result = run_async(_run())
        logger.info("exchange_rate_refresh_completed", result=result)
        return result

    except MaxRetriesExceededError:
        logger.error("exchange_rate_refresh_max_retries_exceeded")
        # In production: push to dead_letter queue for manual replay
        celery_app.send_task(
            "app.workers.tasks.dead_letter_handler",
            args=["refresh_exchange_rates_task", {}],
            queue="dead_letter",
        )

    except Exception as exc:
        logger.warning("exchange_rate_refresh_failed", error=str(exc))
        raise


@celery_app.task(
    bind=True,
    name="app.workers.tasks.send_notification_task",
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_notification_task(self, user_id: str, notification_type: str, payload: dict):
    """
    Send notifications (email, push, SMS) asynchronously.
    Decoupled from the API so the user gets instant response
    while the notification is queued.
    """
    logger.info(
        "notification_queued",
        user_id=user_id,
        type=notification_type,
    )
    # TODO: integrate with email provider (SendGrid, SES) or push service
    return {"user_id": user_id, "type": notification_type, "status": "sent"}


@celery_app.task(
    name="app.workers.tasks.audit_log_task",
    max_retries=3,
    autoretry_for=(Exception,),
)
def audit_log_task(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    ip_address: Optional[str],
    details: Optional[dict],
):
    """
    Write an audit log entry asynchronously.
    Keeps audit logging off the critical path.
    """
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.models import AuditLog
        import json

        async with AsyncSessionLocal() as db:
            import uuid
            log = AuditLog(
                user_id=uuid.UUID(user_id) if user_id else None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                details=json.dumps(details) if details else None,
            )
            db.add(log)
            await db.commit()

    run_async(_run())
    logger.info("audit_log_written", action=action, resource_type=resource_type)


@celery_app.task(name="app.workers.tasks.dead_letter_handler", queue="dead_letter")
def dead_letter_handler(original_task_name: str, args: dict):
    """
    Receives permanently failed tasks.
    In production: alert on-call, store to DB for replay dashboard.
    """
    logger.error(
        "dead_letter_received",
        original_task=original_task_name,
        args=args,
    )
    # TODO: persist to dead_letter_jobs table and alert ops team
