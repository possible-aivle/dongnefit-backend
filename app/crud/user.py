"""CRUD operations for users."""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserQuery, UserUpdate


class CRUDUser(CRUDBase[User]):
    """CRUD operations for User model."""

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_provider_id(self, db: AsyncSession, provider_id: str) -> User | None:
        """Get user by OAuth provider ID."""
        result = await db.execute(select(User).where(User.id == provider_id))
        return result.scalar_one_or_none()

    async def get_multi_with_query(
        self,
        db: AsyncSession,
        *,
        query: UserQuery,
    ) -> tuple[list[User], int]:
        """Get users with filtering, sorting, and pagination."""
        conditions = []

        if query.search:
            search_term = f"%{query.search}%"
            conditions.append(
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term),
                )
            )

        if query.role:
            conditions.append(User.role == query.role.value)

        if query.is_active is not None:
            conditions.append(User.is_active == query.is_active)

        if query.provider:
            conditions.append(User.provider == query.provider.value)

        where_clause = and_(*conditions) if conditions else True

        # Order by
        order_by = User.created_at.desc()
        if query.sort_by == "oldest":
            order_by = User.created_at.asc()
        elif query.sort_by == "name":
            order_by = User.name.asc()

        # Get users
        result = await db.execute(
            select(User)
            .where(where_clause)
            .order_by(order_by)
            .offset(query.offset)
            .limit(query.limit)
        )
        users = list(result.scalars().all())

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(User).where(where_clause)
        )
        total = count_result.scalar() or 0

        return users, total

    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        db_obj = User(
            id=f"{obj_in.provider.value}:{obj_in.email}",  # Generate OAuth-style ID
            email=obj_in.email,
            name=obj_in.name,
            profile_image_url=obj_in.profile_image_url,
            role=obj_in.role.value,
            provider=obj_in.provider.value,
            phone=obj_in.phone,
            is_active=True,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_user(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate,
    ) -> User:
        """Update user profile."""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)

    async def update_role(self, db: AsyncSession, *, db_obj: User, role: str) -> User:
        """Update user role."""
        db_obj.role = role
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def deactivate(self, db: AsyncSession, *, db_obj: User) -> User:
        """Deactivate a user."""
        db_obj.is_active = False
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def activate(self, db: AsyncSession, *, db_obj: User) -> User:
        """Activate a user."""
        db_obj.is_active = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_last_login(self, db: AsyncSession, *, db_obj: User) -> User:
        """Update last login timestamp."""
        db_obj.last_login_at = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


user = CRUDUser(User)
