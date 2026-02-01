"""Discussion model for community forums."""

from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class DiscussionType(str, Enum):
    """Type of discussion post."""

    GENERAL = "general"
    QUESTION = "question"
    ANNOUNCEMENT = "announcement"


class Discussion(Base, TimestampMixin):
    """Community discussion post model."""

    __tablename__ = "discussions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    neighborhood_id: Mapped[int | None] = mapped_column(
        ForeignKey("neighborhoods.id", ondelete="SET NULL"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default=DiscussionType.GENERAL.value, nullable=False)

    # Stats
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DiscussionReply(Base, TimestampMixin):
    """Reply to a discussion."""

    __tablename__ = "discussion_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discussion_id: Mapped[int] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("discussion_replies.id", ondelete="CASCADE"), nullable=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DiscussionLike(Base, TimestampMixin):
    """Like on a discussion or reply."""

    __tablename__ = "discussion_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    discussion_id: Mapped[int | None] = mapped_column(
        ForeignKey("discussions.id", ondelete="CASCADE"), nullable=True
    )
    reply_id: Mapped[int | None] = mapped_column(
        ForeignKey("discussion_replies.id", ondelete="CASCADE"), nullable=True
    )
