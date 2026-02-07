"""Blog schemas."""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema
from app.schemas.user import UserPublic


class BlogStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# === Request Schemas ===


class BlogCreate(BaseSchema):
    """Schema for creating a blog post."""

    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    content: str
    excerpt: str | None = None
    cover_image: str | None = None
    status: BlogStatus = BlogStatus.DRAFT
    is_featured: bool = False
    meta_title: str | None = Field(None, max_length=255)
    meta_description: str | None = Field(None, max_length=500)


class BlogUpdate(BaseSchema):
    """Schema for updating a blog post."""

    title: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    excerpt: str | None = None
    cover_image: str | None = None
    status: BlogStatus | None = None
    is_featured: bool | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class BlogQuery(PaginationParams):
    """Query parameters for listing blog posts."""

    search: str | None = None
    status: BlogStatus | None = None
    is_featured: bool | None = None
    sort_by: str = "newest"  # newest, popular


# === Response Schemas ===


class BlogResponse(TimestampSchema):
    """Blog post response."""

    id: int
    author_id: str
    title: str
    slug: str
    content: str
    excerpt: str | None
    cover_image: str | None
    status: BlogStatus
    is_featured: bool
    published_at: datetime | None
    meta_title: str | None
    meta_description: str | None
    view_count: int


class BlogSummary(BaseSchema):
    """Blog summary for lists."""

    id: int
    title: str
    slug: str
    excerpt: str | None
    cover_image: str | None
    status: BlogStatus
    is_featured: bool
    published_at: datetime | None
    view_count: int


class BlogWithAuthor(BlogResponse):
    """Blog with author details."""

    author: UserPublic | None = None
