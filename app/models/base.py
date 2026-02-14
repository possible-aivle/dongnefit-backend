"""Base model mixins."""

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def get_utc_now() -> datetime:
    """Get current UTC time (naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin(SQLModel):
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)


class PublicDataBase(SQLModel):
    """공공데이터 공통 필드 믹스인.

    모든 공공데이터 테이블이 상속받는 베이스.
    raw_data JSONB로 원본 데이터를 보관하여 추후 컬럼 확장 시 재처리 가능.
    """

    id: int | None = Field(default=None, primary_key=True)
    raw_data: dict | None = Field(
        default=None,
        sa_type=JSONB,
        description="원본 데이터 (전처리 전 원본 보관)",
    )
    collected_at: datetime = Field(
        default_factory=get_utc_now,
        description="데이터 수집 일시",
    )
    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)
