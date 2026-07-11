"""
FastAPI dependency injection functions.

Dependencies are injected into route handlers by FastAPI.
This keeps route handlers thin — they don't construct services manually.

Design rationale:
- get_current_user is reusable across all protected endpoints.
- Services receive the DB session from the DI system, not constructed themselves.
- This pattern makes testing easy: override dependencies with mocks.
"""
import uuid

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.exceptions import AuthenticationException
from app.models import User
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT and return the authenticated User model.
    Raises 401 on invalid/expired token or if user does not exist.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN_TYPE", "message": "Not an access token."},
        )

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject is invalid."},
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found or deactivated."},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias for clarity — same as get_current_user but named for readability."""
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Restrict endpoint to admin users only."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access required."},
        )
    return current_user


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
) -> str | None:
    """Extract optional idempotency key from request headers."""
    return idempotency_key
