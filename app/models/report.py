"""Report model for neighborhood content."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class ReportStatus(Enum):
    """Report publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ReportCategory(Base, TimestampMixin):
    """Category for reports."""

    __tablename__ = "report_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Report(Base, TimestampMixin):
    """Neighborhood report/content model."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    neighborhood_id: Mapped[int] = mapped_column(
        ForeignKey("neighborhoods.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_categories.id", ondelete="SET NULL"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Status & Stats
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.DRAFT.value, nullable=False
    )
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    featured_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportReview(Base, TimestampMixin):
    """Review for a report."""

    __tablename__ = "report_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
