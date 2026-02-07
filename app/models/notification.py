"""Notification model for user alerts."""

from enum import Enum

from sqlmodel import Field

from app.models.base import TimestampMixin


class NotificationType(Enum):
    """Notification type enum."""

    MENTION = "mention"
    REPLY = "reply"
    LIKE = "like"
    SYSTEM = "system"
    PAYMENT = "payment"
    REPORT = "report"


class Notification(TimestampMixin, table=True):
    """User notification model."""

    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    type: str = Field(max_length=30)
    title: str = Field(max_length=255)
    message: str
    related_id: int | None = Field(default=None)  # FK to related entity
    related_type: str | None = Field(default=None, max_length=50)  # Entity type
    is_read: bool = Field(default=False)


class NotificationSettings(TimestampMixin, table=True):
    """User notification preferences."""

    __tablename__ = "notification_settings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", max_length=255, unique=True, ondelete="CASCADE")
    email_enabled: bool = Field(default=True)
    push_enabled: bool = Field(default=True)
    mention_enabled: bool = Field(default=True)
    reply_enabled: bool = Field(default=True)
    like_enabled: bool = Field(default=True)
    system_enabled: bool = Field(default=True)
    marketing_enabled: bool = Field(default=False)
