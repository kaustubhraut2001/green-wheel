"""
Authentication Service — business logic for registration, login, token management.

Business logic lives here, never in the API route handlers.
Routes call services. Services call repositories.
"""
import hashlib
import uuid
from datetime import datetime, timezone

import structlog

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.redis import get_redis_client
from app.exceptions import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
)
from app.models import RefreshToken, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Pre-compute a valid bcrypt hash once at module load so that verify_password
# can always run successfully even when no user is found. This prevents the
# "malformed bcrypt hash" exception that previously caused ~15-second delays.
_DUMMY_HASH: str = hash_password("__timing_guard_dummy_password__")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, request: UserRegisterRequest) -> UserResponse:
        """
        Register a new user.
        1. Check email uniqueness
        2. Hash password
        3. Persist user
        4. Return response (no tokens at registration — force explicit login)
        """
        if await self.user_repo.email_exists(request.email):
            raise ConflictException(f"Email '{request.email}' is already registered.")

        hashed = hash_password(request.password)
        user = await self.user_repo.create(
            email=request.email,
            hashed_password=hashed,
            first_name=request.first_name,
            last_name=request.last_name,
            default_currency=request.default_currency,
        )
        await self.db.commit()

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return UserResponse.model_validate(user)

    async def login(self, request: UserLoginRequest) -> TokenResponse:
        """
        Authenticate a user and return access + refresh tokens.
        Timing-safe comparison via verify_password (bcrypt).
        """
        user = await self.user_repo.get_by_email(request.email)

        # Always run verify_password even if user not found to prevent user
        # enumeration via timing attacks. The dummy hash MUST be a valid bcrypt
        # hash — an invalid one causes passlib to raise "malformed bcrypt hash"
        # which bypasses the timing protection and causes a 15-second stall.
        # _DUMMY_HASH is pre-computed once at import time (see module level).
        stored_hash = user.hashed_password if user else _DUMMY_HASH

        if not verify_password(request.password, stored_hash) or user is None:
            raise AuthenticationException("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationException("Account is deactivated. Please contact support.")

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        # Store refresh token hash in DB for revocation support
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=str(datetime.now(timezone.utc).isoformat()),
        )
        self.db.add(rt)
        await self.db.commit()

        logger.info("user_logged_in", user_id=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Exchange a valid refresh token for a new access token.
        Validates token signature, checks DB for revocation.
        """
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise AuthenticationException("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise AuthenticationException("Token is not a refresh token.")

        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        from sqlalchemy import select
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
        )
        rt = result.scalar_one_or_none()
        if not rt:
            raise AuthenticationException("Refresh token has been revoked or does not exist.")

        user_id = payload["sub"]
        new_access_token = create_access_token(subject=user_id)

        logger.info("token_refreshed", user_id=user_id)
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token in DB."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        from sqlalchemy import select, update
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True)
        )
        await self.db.commit()
