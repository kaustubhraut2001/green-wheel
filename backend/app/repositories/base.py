"""
Repository Pattern — base class.

The repository pattern decouples data access from business logic.
Benefits:
- Services never write SQL — they call repository methods.
- Repositories can be swapped (e.g., different DB) without touching services.
- Easy to mock in unit tests.

All repositories receive an AsyncSession injected by FastAPI's DI system.
"""
from typing import Generic, List, Optional, Type, TypeVar
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 20) -> List[ModelType]:
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def save(self, instance: ModelType) -> ModelType:
        self.db.add(instance)
        await self.db.flush()  # flush to get DB-generated values (e.g., created_at)
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()
