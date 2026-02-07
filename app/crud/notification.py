"""CRUD operations for notifications."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, func, select

from app.crud.base import CRUDBase
from app.models.notification import Notification, NotificationSettings
from app.schemas.notification import (
    NotificationCreate,
    NotificationQuery,
    NotificationSettingsUpdate,
)


class CRUDNotification(CRUDBase[Notification]):
    """CRUD operations for Notification model."""

    async def get_user_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        query: NotificationQuery,
    ) -> tuple[list[Notification], int]:
        """Get notifications for a user."""
        conditions = [Notification.user_id == user_id]

        if query.type:
            conditions.append(Notification.type == query.type.value)

        if query.is_read is not None:
            conditions.append(Notification.is_read == query.is_read)

        where_clause = and_(*conditions)

        result = await db.execute(
            select(Notification)
            .where(where_clause)
            .order_by(Notification.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        notifications = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Notification).where(where_clause)
        )
        total = count_result.scalar() or 0

        return notifications, total

    async def create_notification(
        self,
        db: AsyncSession,
        *,
        obj_in: NotificationCreate,
    ) -> Notification:
        """Create a new notification."""
        db_obj = Notification(
            user_id=obj_in.user_id,
            type=obj_in.type.value,
            title=obj_in.title,
            message=obj_in.message,
            related_id=obj_in.related_id,
            related_type=obj_in.related_type,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def mark_as_read(
        self,
        db: AsyncSession,
        *,
        db_obj: Notification,
    ) -> Notification:
        """Mark a notification as read."""
        db_obj.is_read = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> int:
        """Mark all notifications as read for a user."""
        result = await db.execute(
            Notification.__table__.update()
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True)
        )
        return result.rowcount

    async def get_unread_count(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> int:
        """Get unread notification count for a user."""
        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
        )
        return result.scalar() or 0


class CRUDNotificationSettings(CRUDBase[NotificationSettings]):
    """CRUD operations for NotificationSettings model."""

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> NotificationSettings | None:
        """Get notification settings for a user."""
        result = await db.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> NotificationSettings:
        """Get or create notification settings for a user."""
        settings = await self.get_by_user(db, user_id=user_id)
        if not settings:
            settings = NotificationSettings(user_id=user_id)
            db.add(settings)
            await db.flush()
            await db.refresh(settings)
        return settings

    async def update_settings(
        self,
        db: AsyncSession,
        *,
        db_obj: NotificationSettings,
        obj_in: NotificationSettingsUpdate,
    ) -> NotificationSettings:
        """Update notification settings."""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


notification = CRUDNotification(Notification)
notification_settings = CRUDNotificationSettings(NotificationSettings)
