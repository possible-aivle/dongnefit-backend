"""Blog model for admin posts."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field

from app.models.base import TimestampMixin


class BlogStatus(Enum):
    """Blog post status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BlogPost(TimestampMixin, table=True):
    """Blog post model (admin only)."""

    __tablename__ = "blog_posts"

    id: int | None = Field(default=None, primary_key=True)
    author_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")

    # Content
    title: str = Field(max_length=255)
    slug: str = Field(max_length=255, unique=True, index=True)
    content: str
    excerpt: str | None = Field(default=None)
    cover_image: str | None = Field(default=None, max_length=500)

    # Status
    status: str = Field(default=BlogStatus.DRAFT.value, max_length=20)
    is_featured: bool = Field(default=False)
    published_at: datetime | None = Field(default=None)

    # SEO
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = Field(default=None, max_length=500)

    # Stats
    view_count: int = Field(default=0)
