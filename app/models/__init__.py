"""Database models."""

from app.models.base import TimestampMixin
from app.models.content import GeneratedContent
from app.models.property import Property

__all__ = [
    "TimestampMixin",
    "Property",
    "GeneratedContent",
]
