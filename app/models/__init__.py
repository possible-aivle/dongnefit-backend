"""Database models."""

from app.models.base import TimestampMixin
from app.models.blog import BlogPost, BlogStatus
from app.models.discussion import (
    Discussion,
    DiscussionLike,
    DiscussionReply,
    DiscussionType,
)
from app.models.file import FileStorage
from app.models.neighborhood import Neighborhood
from app.models.notification import Notification, NotificationSettings, NotificationType
from app.models.report import Report, ReportCategory, ReportReview, ReportStatus
from app.models.user import AuthProvider, User, UserRole

__all__ = [
    # Base
    "TimestampMixin",
    # User
    "User",
    "UserRole",
    "AuthProvider",
    # Neighborhood
    "Neighborhood",
    # Report
    "Report",
    "ReportCategory",
    "ReportReview",
    "ReportStatus",
    # Discussion
    "Discussion",
    "DiscussionReply",
    "DiscussionLike",
    "DiscussionType",
    # Notification
    "Notification",
    "NotificationSettings",
    "NotificationType",
    # Blog
    "BlogPost",
    "BlogStatus",
    # File
    "FileStorage",
]
