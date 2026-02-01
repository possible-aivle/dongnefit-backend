"""Report schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema
from app.schemas.neighborhood import NeighborhoodSummary
from app.schemas.user import UserPublic


class ReportStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# === Request Schemas ===


class ReportCategoryCreate(BaseSchema):
    """Schema for creating a report category."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ReportCreate(BaseSchema):
    """Schema for creating a report."""

    neighborhood_id: int
    category_id: int | None = None
    title: str = Field(..., min_length=1, max_length=255)
    subtitle: str | None = Field(None, max_length=500)
    cover_image: str | None = None
    summary: str | None = None
    content: str
    price: Decimal = Field(default=0, ge=0)
    original_price: Decimal | None = Field(None, ge=0)
    tags: list[str] | None = None
    meta_description: str | None = Field(None, max_length=500)


class ReportUpdate(BaseSchema):
    """Schema for updating a report."""

    category_id: int | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    subtitle: str | None = None
    cover_image: str | None = None
    summary: str | None = None
    content: str | None = None
    price: Decimal | None = Field(None, ge=0)
    original_price: Decimal | None = None
    tags: list[str] | None = None
    meta_description: str | None = None
    status: ReportStatus | None = None


class ReportQuery(PaginationParams):
    """Query parameters for listing reports."""

    search: str | None = None
    neighborhood_id: int | None = None
    category_id: int | None = None
    status: ReportStatus | None = None
    author_id: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort_by: str = "newest"  # newest, popular, rating, price_low, price_high


class ReportReviewCreate(BaseSchema):
    """Schema for creating a report review."""

    rating: int = Field(..., ge=1, le=5)
    content: str | None = None


# === Response Schemas ===


class ReportCategoryResponse(TimestampSchema):
    """Report category response."""

    id: int
    name: str
    slug: str
    description: str | None


class ReportResponse(TimestampSchema):
    """Report response."""

    id: int
    author_id: str
    neighborhood_id: int
    category_id: int | None
    title: str
    subtitle: str | None
    cover_image: str | None
    summary: str | None
    content: str
    price: Decimal
    original_price: Decimal | None
    status: ReportStatus
    purchase_count: int
    rating: Decimal
    review_count: int
    tags: list[str] | None
    meta_description: str | None
    featured_until: datetime | None
    published_at: datetime | None
    last_updated: datetime | None


class ReportSummary(BaseSchema):
    """Report summary for lists."""

    id: int
    title: str
    subtitle: str | None
    cover_image: str | None
    price: Decimal
    original_price: Decimal | None
    rating: Decimal
    review_count: int
    status: ReportStatus


class ReportWithDetails(ReportResponse):
    """Report with related data."""

    author: UserPublic | None = None
    neighborhood: NeighborhoodSummary | None = None
    category: ReportCategoryResponse | None = None


class ReportReviewResponse(TimestampSchema):
    """Report review response."""

    id: int
    report_id: int
    user_id: str
    rating: int
    content: str | None
    user: UserPublic | None = None
