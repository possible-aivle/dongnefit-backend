"""Discussion schemas."""

from enum import Enum

from pydantic import Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema
from app.schemas.neighborhood import NeighborhoodSummary
from app.schemas.user import UserPublic


class DiscussionType(Enum):
    GENERAL = "general"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"


# === Request Schemas ===


class DiscussionCreate(BaseSchema):
    """Schema for creating a discussion."""

    neighborhood_id: int | None = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    type: DiscussionType = DiscussionType.GENERAL


class DiscussionUpdate(BaseSchema):
    """Schema for updating a discussion."""

    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    type: DiscussionType | None = None


class DiscussionQuery(PaginationParams):
    """Query parameters for listing discussions."""

    search: str | None = None
    neighborhood_id: int | None = None
    user_id: str | None = None
    type: DiscussionType | None = None
    sort_by: str = "newest"  # newest, popular, most_replies


class DiscussionReplyCreate(BaseSchema):
    """Schema for creating a reply."""

    content: str = Field(..., min_length=1)
    parent_id: int | None = None


class DiscussionReplyUpdate(BaseSchema):
    """Schema for updating a reply."""

    content: str = Field(..., min_length=1)


# === Response Schemas ===


class DiscussionResponse(TimestampSchema):
    """Discussion response."""

    id: int
    user_id: str
    neighborhood_id: int | None
    title: str
    content: str
    type: DiscussionType
    like_count: int
    reply_count: int
    view_count: int
    is_edited: bool


class DiscussionSummary(BaseSchema):
    """Discussion summary for lists."""

    id: int
    title: str
    type: DiscussionType
    like_count: int
    reply_count: int
    view_count: int


class DiscussionWithDetails(DiscussionResponse):
    """Discussion with related data."""

    user: UserPublic | None = None
    neighborhood: NeighborhoodSummary | None = None
    is_liked: bool = False


class DiscussionReplyResponse(TimestampSchema):
    """Discussion reply response."""

    id: int
    discussion_id: int
    user_id: str
    parent_id: int | None
    content: str
    like_count: int
    is_edited: bool
    user: UserPublic | None = None
    is_liked: bool = False
