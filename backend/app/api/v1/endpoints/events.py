"""
Server-Sent Events (SSE) endpoint.

Why SSE over WebSockets?
- Transfers are server→client only (no need for bidirectional).
- SSE works over plain HTTP/1.1, no protocol upgrade needed.
- Automatic reconnection is built into the browser EventSource API.
- Much simpler than WebSockets for this use case.

Flow:
1. Browser connects to /api/v1/events/stream with JWT in query param.
2. Server keeps the connection open and publishes events via Redis pub/sub.
3. When a transfer/credit/debit completes, the service publishes to Redis channel.
4. SSE endpoint picks it up and pushes to the correct user's connection.

Redis Pub/Sub channel naming:
  wallet:events:{user_id}  →  personal events for that user
"""
import asyncio
import json
import uuid

import structlog
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.core.security import decode_token
from app.db.redis import get_redis_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/events", tags=["Real-time Events"])

HEARTBEAT_INTERVAL = 25  # seconds — keeps connection alive through proxies


def user_channel(user_id: str) -> str:
    return f"wallet:events:{user_id}"


async def event_generator(request: Request, user_id: str):
    """
    Async generator that yields SSE-formatted strings.
    Subscribes to the user's Redis channel and forwards messages to the browser.
    Sends a heartbeat comment every 25s to prevent proxy timeouts.
    """
    redis = get_redis_client()
    pubsub = redis.pubsub()
    channel = user_channel(user_id)

    await pubsub.subscribe(channel)
    logger.info("sse_client_connected", user_id=user_id, channel=channel)

    # Send initial connected event
    yield f"event: connected\ndata: {json.dumps({'user_id': user_id})}\n\n"

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            # Non-blocking message check with short timeout
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                message = None

            if message and message.get("type") == "message":
                data = message.get("data", "")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"event: wallet_update\ndata: {data}\n\n"
                logger.debug("sse_event_sent", user_id=user_id)
            else:
                # Heartbeat — keeps connection alive through nginx/proxies
                yield f": heartbeat\n\n"
                await asyncio.sleep(HEARTBEAT_INTERVAL)

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("sse_generator_error", user_id=user_id, error=str(exc))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        logger.info("sse_client_disconnected", user_id=user_id)


@router.get("/stream")
async def sse_stream(
    request: Request,
    token: str = Query(..., description="JWT access token"),
):
    """
    SSE stream endpoint.
    Token is passed as query param because EventSource API doesn't support headers.

    Usage from browser:
        const source = new EventSource(`/api/v1/events/stream?token=${accessToken}`);
        source.addEventListener('wallet_update', (e) => {
            const data = JSON.parse(e.data);
            // update UI
        });
    """
    # Validate JWT
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"error": "Invalid token"})

    return StreamingResponse(
        event_generator(request, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering
            "Connection": "keep-alive",
        },
    )
