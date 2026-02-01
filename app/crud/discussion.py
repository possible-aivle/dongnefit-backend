"""CRUD operations for discussions."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.discussion import Discussion, DiscussionLike, DiscussionReply
from app.schemas.discussion import (
    DiscussionCreate,
    DiscussionQuery,
    DiscussionReplyCreate,
    DiscussionUpdate,
)


class CRUDDiscussion(CRUDBase[Discussion]):
    """CRUD operations for Discussion model."""

    async def get_multi_with_query(
        self,
        db: AsyncSession,
        *,
        query: DiscussionQuery,
    ) -> tuple[list[Discussion], int]:
        """Get discussions with filtering and pagination."""
        conditions = []

        if query.search:
            search_term = f"%{query.search}%"
            conditions.append(
                or_(
                    Discussion.title.ilike(search_term),
                    Discussion.content.ilike(search_term),
                )
            )

        if query.neighborhood_id:
            conditions.append(Discussion.neighborhood_id == query.neighborhood_id)

        if query.user_id:
            conditions.append(Discussion.user_id == query.user_id)

        if query.type:
            conditions.append(Discussion.type == query.type.value)

        where_clause = and_(*conditions) if conditions else True

        # Order by
        order_by = Discussion.created_at.desc()
        if query.sort_by == "popular":
            order_by = Discussion.like_count.desc()
        elif query.sort_by == "most_replies":
            order_by = Discussion.reply_count.desc()

        # Get discussions
        result = await db.execute(
            select(Discussion)
            .where(where_clause)
            .order_by(order_by)
            .offset(query.offset)
            .limit(query.limit)
        )
        discussions = list(result.scalars().all())

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(Discussion).where(where_clause)
        )
        total = count_result.scalar() or 0

        return discussions, total

    async def create_discussion(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        obj_in: DiscussionCreate,
    ) -> Discussion:
        """Create a new discussion."""
        db_obj = Discussion(
            user_id=user_id,
            neighborhood_id=obj_in.neighborhood_id,
            title=obj_in.title,
            content=obj_in.content,
            type=obj_in.type.value,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_discussion(
        self,
        db: AsyncSession,
        *,
        db_obj: Discussion,
        obj_in: DiscussionUpdate,
    ) -> Discussion:
        """Update a discussion."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "type" in update_data:
            update_data["type"] = update_data["type"].value
        update_data["is_edited"] = True
        return await self.update(db, db_obj=db_obj, obj_in=update_data)

    async def increment_view_count(
        self,
        db: AsyncSession,
        *,
        db_obj: Discussion,
    ) -> Discussion:
        """Increment view count."""
        db_obj.view_count += 1
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_reply_count(
        self,
        db: AsyncSession,
        *,
        discussion_id: int,
    ) -> None:
        """Update reply count for a discussion."""
        count_result = await db.execute(
            select(func.count())
            .select_from(DiscussionReply)
            .where(DiscussionReply.discussion_id == discussion_id)
        )
        count = count_result.scalar() or 0

        await db.execute(
            Discussion.__table__.update()
            .where(Discussion.id == discussion_id)
            .values(reply_count=count)
        )


class CRUDDiscussionReply(CRUDBase[DiscussionReply]):
    """CRUD operations for DiscussionReply model."""

    async def get_by_discussion(
        self,
        db: AsyncSession,
        *,
        discussion_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> list[DiscussionReply]:
        """Get replies for a discussion."""
        result = await db.execute(
            select(DiscussionReply)
            .where(DiscussionReply.discussion_id == discussion_id)
            .order_by(DiscussionReply.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_reply(
        self,
        db: AsyncSession,
        *,
        discussion_id: int,
        user_id: str,
        obj_in: DiscussionReplyCreate,
    ) -> DiscussionReply:
        """Create a new reply."""
        db_obj = DiscussionReply(
            discussion_id=discussion_id,
            user_id=user_id,
            parent_id=obj_in.parent_id,
            content=obj_in.content,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_reply(
        self,
        db: AsyncSession,
        *,
        db_obj: DiscussionReply,
        content: str,
    ) -> DiscussionReply:
        """Update a reply."""
        db_obj.content = content
        db_obj.is_edited = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDDiscussionLike(CRUDBase[DiscussionLike]):
    """CRUD operations for DiscussionLike model."""

    async def get_like(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        discussion_id: int | None = None,
        reply_id: int | None = None,
    ) -> DiscussionLike | None:
        """Get a like by user and target."""
        conditions = [DiscussionLike.user_id == user_id]
        if discussion_id:
            conditions.append(DiscussionLike.discussion_id == discussion_id)
        if reply_id:
            conditions.append(DiscussionLike.reply_id == reply_id)

        result = await db.execute(
            select(DiscussionLike).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def toggle_like(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        discussion_id: int | None = None,
        reply_id: int | None = None,
    ) -> bool:
        """Toggle like on a discussion or reply. Returns True if liked, False if unliked."""
        existing = await self.get_like(
            db,
            user_id=user_id,
            discussion_id=discussion_id,
            reply_id=reply_id,
        )

        if existing:
            await db.delete(existing)
            await db.flush()
            return False
        else:
            db_obj = DiscussionLike(
                user_id=user_id,
                discussion_id=discussion_id,
                reply_id=reply_id,
            )
            db.add(db_obj)
            await db.flush()
            return True

    async def is_liked(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        discussion_id: int | None = None,
        reply_id: int | None = None,
    ) -> bool:
        """Check if user has liked a discussion or reply."""
        like = await self.get_like(
            db,
            user_id=user_id,
            discussion_id=discussion_id,
            reply_id=reply_id,
        )
        return like is not None


discussion = CRUDDiscussion(Discussion)
discussion_reply = CRUDDiscussionReply(DiscussionReply)
discussion_like = CRUDDiscussionLike(DiscussionLike)
