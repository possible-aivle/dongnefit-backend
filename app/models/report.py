"""Report model for neighborhood content."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import TimestampMixin, geometry_column


class ReportStatus(Enum):
    """Report publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReportCategory(TimestampMixin, table=True):
    """Category for reports."""

    __tablename__ = "report_categories"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100, unique=True, index=True)
    description: str | None = Field(default=None)


class Report(TimestampMixin, table=True):
    """Neighborhood report/content model."""

    __tablename__ = "reports"

    id: int | None = Field(default=None, primary_key=True)
    author_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    neighborhood_id: int = Field(foreign_key="neighborhoods.id", ondelete="CASCADE")
    category_id: int | None = Field(
        default=None, foreign_key="report_categories.id", ondelete="SET NULL"
    )
    pnu: str | None = Field(default=None, max_length=19, index=True)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    geometry: Any = geometry_column(description="필지 경계 (Polygon/MultiPolygon)")

    # Content
    title: str = Field(max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    cover_image: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None)
    content: str  # Markdown

    # Pricing
    price: Decimal = Field(default=Decimal("0"), max_digits=10, decimal_places=2)
    original_price: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # Status & Stats
    status: str = Field(default=ReportStatus.DRAFT.value, max_length=20)
    purchase_count: int = Field(default=0)
    rating: Decimal = Field(default=Decimal("0"), max_digits=2, decimal_places=1)
    review_count: int = Field(default=0)
    comment_count: int = Field(default=0)

    # Metadata
    tags: list | None = Field(default=None, sa_column=Column(JSON))
    meta_description: str | None = Field(default=None, max_length=500)
    featured_until: datetime | None = Field(default=None)
    published_at: datetime | None = Field(default=None)
    last_updated: datetime | None = Field(default=None)


class ReportComment(TimestampMixin, table=True):
    """Comment on a report."""

    __tablename__ = "report_comments"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", ondelete="CASCADE")
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    parent_id: int | None = Field(
        default=None, foreign_key="report_comments.id", ondelete="CASCADE"
    )

    content: str
    like_count: int = Field(default=0)
    is_edited: bool = Field(default=False)


class ReportReview(TimestampMixin, table=True):
    """Review for a report."""

    __tablename__ = "report_reviews"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", ondelete="CASCADE")
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    rating: int  # 1-5
    content: str | None = Field(default=None)
