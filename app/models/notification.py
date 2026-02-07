"""Notification model for user alerts."""

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class NotificationType(Enum):
    """Notification type enum."""

    MENTION = "mention"
    REPLY = "reply"
    LIKE = "like"
    SYSTEM = "system"
    PAYMENT = "payment"
    REPORT = "report"


class Notification(Base, TimestampMixin):
    """User notification model."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK to related entity
    related_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Entity type
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class NotificationSettings(Base, TimestampMixin):
    """User notification preferences."""

    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mention_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reply_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    like_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    system_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
