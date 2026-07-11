"""
Real-time event publisher.

After any balance-changing operation (credit, debit, transfer),
services call publish_wallet_event() to push the update to connected SSE clients.

The event payload contains everything the frontend needs to update the UI
without a separate API call:
  - Updated wallet balances
  - The transaction that just occurred
  - Who was affected (sender + recipient for transfers)
"""
import json
import uuid
from decimal import Decimal

import structlog

from app.db.redis import get_redis_client

logger = structlog.get_logger(__name__)


def _serialise(obj):
    """JSON serialiser that handles UUID and Decimal."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def user_channel(user_id: str) -> str:
    return f"wallet:events:{user_id}"


async def publish_wallet_event(
    user_id: uuid.UUID,
    event_type: str,
    wallet_id: uuid.UUID,
    currency: str,
    new_balance: Decimal,
    amount: Decimal,
    transaction_type: str,
    reference: str | None = None,
    note: str | None = None,
    exchange_rate: Decimal | None = None,
) -> None:
    """
    Publish a wallet update event to the user's Redis pub/sub channel.
    Non-blocking — if Redis is unavailable, log and continue (don't fail the transaction).
    """
    payload = {
        "event_type": event_type,
        "wallet_id": wallet_id,
        "currency": currency,
        "new_balance": new_balance,
        "amount": amount,
        "transaction_type": transaction_type,
        "reference": reference,
        "note": note,
        "exchange_rate": exchange_rate,
    }

    try:
        redis = get_redis_client()
        channel = user_channel(str(user_id))
        message = json.dumps(payload, default=_serialise)
        await redis.publish(channel, message)
        logger.debug("wallet_event_published", user_id=str(user_id), event_type=event_type)
    except Exception as exc:
        # Never let event publishing break the main transaction
        logger.warning("wallet_event_publish_failed", error=str(exc), user_id=str(user_id))


async def publish_transfer_event(
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    sender_wallet_id: uuid.UUID,
    recipient_wallet_id: uuid.UUID,
    sender_currency: str,
    recipient_currency: str,
    sender_new_balance: Decimal,
    recipient_new_balance: Decimal,
    amount: Decimal,
    converted_amount: Decimal,
    exchange_rate: Decimal | None,
    reference: str,
    note: str | None = None,
) -> None:
    """
    Publish transfer events to BOTH sender and recipient.
    Each gets a personalised payload with their own updated balance.
    """
    redis = get_redis_client()

    # Sender event
    sender_payload = json.dumps({
        "event_type": "transfer_sent",
        "wallet_id": sender_wallet_id,
        "currency": sender_currency,
        "new_balance": sender_new_balance,
        "amount": amount,
        "transaction_type": "transfer",
        "reference": reference,
        "note": note,
        "exchange_rate": exchange_rate,
    }, default=_serialise)

    # Recipient event
    recipient_payload = json.dumps({
        "event_type": "transfer_received",
        "wallet_id": recipient_wallet_id,
        "currency": recipient_currency,
        "new_balance": recipient_new_balance,
        "amount": converted_amount,
        "transaction_type": "transfer",
        "reference": reference,
        "note": note,
        "exchange_rate": exchange_rate,
    }, default=_serialise)

    try:
        await redis.publish(user_channel(str(sender_id)), sender_payload)
        await redis.publish(user_channel(str(recipient_id)), recipient_payload)
        logger.info(
            "transfer_events_published",
            ref=reference,
            sender=str(sender_id),
            recipient=str(recipient_id),
        )
    except Exception as exc:
        logger.warning("transfer_event_publish_failed", error=str(exc))
