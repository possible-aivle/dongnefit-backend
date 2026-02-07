"""Notification schemas."""

from enum import Enum

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema


class NotificationType(Enum):
    MENTION = "mention"
    REPLY = "reply"
    LIKE = "like"
    SYSTEM = "system"
    PAYMENT = "payment"
    REPORT = "report"


# === Request Schemas ===


class NotificationCreate(BaseSchema):
    """Schema for creating a notification (admin/system)."""

    user_id: str
    type: NotificationType
    title: str
    message: str
    related_id: int | None = None
    related_type: str | None = None


class NotificationQuery(PaginationParams):
    """Query parameters for listing notifications."""

    type: NotificationType | None = None
    is_read: bool | None = None


class NotificationSettingsUpdate(BaseSchema):
    """Schema for updating notification settings."""

    email_enabled: bool | None = None
    push_enabled: bool | None = None
    mention_enabled: bool | None = None
    reply_enabled: bool | None = None
    like_enabled: bool | None = None
    system_enabled: bool | None = None
    marketing_enabled: bool | None = None


# === Response Schemas ===


class NotificationResponse(TimestampSchema):
    """Notification response."""

    id: int
    user_id: str
    type: NotificationType
    title: str
    message: str
    related_id: int | None
    related_type: str | None
    is_read: bool


class NotificationSettingsResponse(TimestampSchema):
    """Notification settings response."""

    id: int
    user_id: str
    email_enabled: bool
    push_enabled: bool
    mention_enabled: bool
    reply_enabled: bool
    like_enabled: bool
    system_enabled: bool
    marketing_enabled: bool


class UnreadCountResponse(BaseSchema):
    """Unread notification count."""

    count: int
