"""Discussion model for community forums."""

from enum import Enum

from sqlmodel import Field

from app.models.base import TimestampMixin


class DiscussionType(Enum):
    """Type of discussion post."""

    GENERAL = "general"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"
    EXPERIENCE = "experience"
    TIP = "tip"


class Discussion(TimestampMixin, table=True):
    """Community discussion post model."""

    __tablename__ = "discussions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    neighborhood_id: int | None = Field(
        default=None, foreign_key="neighborhoods.id", ondelete="SET NULL"
    )

    # Content
    title: str = Field(max_length=255)
    content: str
    type: str = Field(default=DiscussionType.GENERAL.value, max_length=20)

    # Stats
    like_count: int = Field(default=0)
    reply_count: int = Field(default=0)
    view_count: int = Field(default=0)
    is_edited: bool = Field(default=False)


class DiscussionReply(TimestampMixin, table=True):
    """Reply to a discussion."""

    __tablename__ = "discussion_replies"

    id: int | None = Field(default=None, primary_key=True)
    discussion_id: int = Field(foreign_key="discussions.id", ondelete="CASCADE")
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    parent_id: int | None = Field(
        default=None, foreign_key="discussion_replies.id", ondelete="CASCADE"
    )

    content: str
    like_count: int = Field(default=0)
    is_edited: bool = Field(default=False)


class DiscussionLike(TimestampMixin, table=True):
    """Like on a discussion or reply."""

    __tablename__ = "discussion_likes"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", max_length=255, ondelete="CASCADE")
    discussion_id: int | None = Field(
        default=None, foreign_key="discussions.id", ondelete="CASCADE"
    )
    reply_id: int | None = Field(
        default=None, foreign_key="discussion_replies.id", ondelete="CASCADE"
    )
