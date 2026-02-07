"""Base CRUD operations."""

from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, func, select

ModelType = TypeVar("ModelType", bound=SQLModel)


class CRUDBase[ModelType: SQLModel]:
    """Base class for CRUD operations."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        result = await db.execute(select(self.model).offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(self, db: AsyncSession) -> int:
        """Count total records."""
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0

    async def create(self, db: AsyncSession, *, obj_in: dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> ModelType | None:
        """Delete a record by ID."""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj
