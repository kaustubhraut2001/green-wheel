"""
Celery application configuration.

Redis is used as both broker and result backend.
- Broker (DB 1): task queue — Celery publishes tasks here
- Result backend (DB 2): task results — optional but useful for monitoring

Retry strategy: exponential backoff with max_retries cap.
Dead Letter: tasks that exhaust retries are logged to a DLQ queue
             (configured via task_routes or a dedicated DLQ handler).
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "wallet_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Retry behaviour
    task_acks_late=True,          # Acknowledge after execution (not before) — prevents message loss
    task_reject_on_worker_lost=True,  # Re-queue if worker crashes mid-task
    worker_prefetch_multiplier=1,  # Fair distribution; prevents one worker starving others
    # Result expiry
    result_expires=3600,
    # DLQ: permanently failed tasks are routed to a dead_letter queue
    task_routes={
        "app.workers.tasks.*": {"queue": "default"},
    },
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "dead_letter": {"exchange": "dead_letter", "routing_key": "dead_letter"},
    },
    # Periodic tasks (beat schedule)
    beat_schedule={
        "refresh-exchange-rates-hourly": {
            "task": "app.workers.tasks.refresh_exchange_rates_task",
            "schedule": crontab(minute=0),  # Every hour
            "options": {"queue": "default"},
        },
    },
)
