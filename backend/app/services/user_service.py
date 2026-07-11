"""
User Service — profile management, image upload.
"""
import os
import uuid
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis import get_redis_client
from app.exceptions import NotFoundException
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserUpdateRequest

logger = structlog.get_logger(__name__)

USER_CACHE_TTL = 300  # 5 minutes


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.redis = get_redis_client()

    def _cache_key(self, user_id: uuid.UUID) -> str:
        return f"user_profile:{user_id}"

    async def get_profile(self, user_id: uuid.UUID) -> UserResponse:
        """Fetch user profile — Redis cache first."""
        cached = await self.redis.get(self._cache_key(user_id))
        if cached:
            import json
            return UserResponse.model_validate_json(cached)

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        response = UserResponse.model_validate(user)
        await self.redis.setex(
            self._cache_key(user_id), USER_CACHE_TTL, response.model_dump_json()
        )
        return response

    async def update_profile(
        self, user_id: uuid.UUID, request: UserUpdateRequest
    ) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        if request.first_name is not None:
            user.first_name = request.first_name
        if request.last_name is not None:
            user.last_name = request.last_name
        if request.default_currency is not None:
            user.default_currency = request.default_currency

        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate cache
        await self.redis.delete(self._cache_key(user_id))

        logger.info("profile_updated", user_id=str(user_id))
        return UserResponse.model_validate(user)

    async def upload_profile_image(
        self, user_id: uuid.UUID, file_content: bytes, filename: str
    ) -> UserResponse:
        """
        Save uploaded profile image and update the user record.
        In production, replace local storage with S3/GCS.
        """
        upload_dir = Path(settings.UPLOAD_DIR) / "profile_images"
        upload_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            from app.exceptions import ValidationException
            raise ValidationException("Only JPG, PNG, and WEBP images are allowed.")

        if len(file_content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            from app.exceptions import ValidationException
            raise ValidationException(
                f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )

        safe_name = f"{user_id}{ext}"
        file_path = upload_dir / safe_name
        file_path.write_bytes(file_content)

        image_url = f"/static/profile_images/{safe_name}"
        user = await self.user_repo.update_profile_image(user_id, image_url)
        if not user:
            raise NotFoundException("User", str(user_id))

        await self.db.commit()
        await self.redis.delete(self._cache_key(user_id))

        logger.info("profile_image_uploaded", user_id=str(user_id), url=image_url)
        return UserResponse.model_validate(user)
