"""Base model mixins."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def get_utc_now() -> datetime:
    """Get current UTC time (naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin(SQLModel):
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)
