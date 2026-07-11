"""
User Repository — all database operations for the User model.
"""
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        email: str,
        hashed_password: str,
        first_name: str,
        last_name: str,
        default_currency: str = "USD",
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            default_currency=default_currency,
        )
        return await self.save(user)

    async def update_profile_image(self, user_id: uuid.UUID, image_url: str) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            user.profile_image_url = image_url
            await self.db.flush()
            await self.db.refresh(user)
        return user
