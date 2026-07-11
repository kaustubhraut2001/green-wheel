"""
Global exception middleware.

Maps domain exceptions → consistent HTTP responses.
Catches unhandled exceptions and returns 500 without leaking stack traces.

Response envelope:
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Wallet not found: abc123"
    }
}
"""
import time
import uuid

import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    DuplicateTransactionException,
    InsufficientFundsException,
    NotFoundException,
    RateLimitException,
    ValidationException,
    WalletSuspendedException,
)

logger = structlog.get_logger(__name__)


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


class ExceptionMiddleware(BaseHTTPMiddleware):
    """
    Catches all exceptions and converts them to structured JSON responses.
    Also injects request_id and measures latency for every request.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind request context so all log lines within this request carry it
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-ID"] = request_id
            return response

        except NotFoundException as exc:
            return _error_response(exc.code, exc.message, status.HTTP_404_NOT_FOUND)

        except (AuthenticationException,) as exc:
            return _error_response(exc.code, exc.message, status.HTTP_401_UNAUTHORIZED)

        except AuthorizationException as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)

        except ConflictException as exc:
            return _error_response(exc.code, exc.message, status.HTTP_409_CONFLICT)

        except DuplicateTransactionException as exc:
            return _error_response(exc.code, exc.message, status.HTTP_409_CONFLICT)

        except (InsufficientFundsException, WalletSuspendedException, ValidationException) as exc:
            return _error_response(exc.code, exc.message, status.HTTP_422_UNPROCESSABLE_ENTITY)

        except RateLimitException as exc:
            return _error_response(exc.code, exc.message, status.HTTP_429_TOO_MANY_REQUESTS)

        except AppException as exc:
            logger.warning("app_exception", code=exc.code, message=exc.message)
            return _error_response(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)

        except Exception as exc:
            logger.exception("unhandled_exception", error=str(exc))
            return _error_response(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred. Please try again later.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with a structured response."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
        },
    )
