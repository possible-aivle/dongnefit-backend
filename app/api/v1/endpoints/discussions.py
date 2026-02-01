"""Discussion endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, CurrentUserOptional
from app.crud.discussion import discussion as discussion_crud
from app.crud.discussion import discussion_like as like_crud
from app.crud.discussion import discussion_reply as reply_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.discussion import (
    DiscussionCreate,
    DiscussionQuery,
    DiscussionReplyCreate,
    DiscussionReplyResponse,
    DiscussionReplyUpdate,
    DiscussionResponse,
    DiscussionUpdate,
    DiscussionWithDetails,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[DiscussionResponse],
    summary="List discussions",
    description="List discussions with pagination and filtering",
)
async def list_discussions(
    query: DiscussionQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DiscussionResponse]:
    """List discussions with filtering and pagination."""
    discussions, total = await discussion_crud.get_multi_with_query(db, query=query)

    return PaginatedResponse(
        data=[DiscussionResponse.model_validate(d) for d in discussions],
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/{discussion_id}",
    response_model=DiscussionWithDetails,
    summary="Get discussion",
    description="Get a specific discussion by ID",
)
async def get_discussion(
    discussion_id: int,
    current_user: CurrentUserOptional = None,
    db: AsyncSession = Depends(get_db),
) -> DiscussionWithDetails:
    """Get a discussion by ID."""
    discussion = await discussion_crud.get(db, discussion_id)
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다",
        )

    # Increment view count
    await discussion_crud.increment_view_count(db, db_obj=discussion)

    # Check if user liked
    is_liked = False
    if current_user:
        is_liked = await like_crud.is_liked(
            db, user_id=current_user.id, discussion_id=discussion_id
        )

    response = DiscussionWithDetails.model_validate(discussion)
    response.is_liked = is_liked
    return response


@router.post(
    "",
    response_model=DiscussionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create discussion",
    description="Create a new discussion post",
)
async def create_discussion(
    discussion_in: DiscussionCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DiscussionResponse:
    """Create a new discussion."""
    discussion = await discussion_crud.create_discussion(
        db, user_id=current_user.id, obj_in=discussion_in
    )
    return DiscussionResponse.model_validate(discussion)


@router.patch(
    "/{discussion_id}",
    response_model=DiscussionResponse,
    summary="Update discussion",
    description="Update a discussion (owner only)",
)
async def update_discussion(
    discussion_id: int,
    discussion_in: DiscussionUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DiscussionResponse:
    """Update a discussion."""
    discussion = await discussion_crud.get(db, discussion_id)
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다",
        )

    if discussion.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="수정 권한이 없습니다",
        )

    discussion = await discussion_crud.update_discussion(
        db, db_obj=discussion, obj_in=discussion_in
    )
    return DiscussionResponse.model_validate(discussion)


@router.delete(
    "/{discussion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete discussion",
    description="Delete a discussion (owner only)",
)
async def delete_discussion(
    discussion_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a discussion."""
    discussion = await discussion_crud.get(db, discussion_id)
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다",
        )

    if discussion.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="삭제 권한이 없습니다",
        )

    await discussion_crud.delete(db, id=discussion_id)


@router.post(
    "/{discussion_id}/like",
    summary="Toggle like",
    description="Toggle like on a discussion",
)
async def toggle_discussion_like(
    discussion_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle like on a discussion."""
    discussion = await discussion_crud.get(db, discussion_id)
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다",
        )

    is_liked = await like_crud.toggle_like(
        db, user_id=current_user.id, discussion_id=discussion_id
    )
    return {"is_liked": is_liked}


# === Replies ===


@router.get(
    "/{discussion_id}/replies",
    response_model=list[DiscussionReplyResponse],
    summary="List replies",
    description="Get replies for a discussion",
)
async def list_replies(
    discussion_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[DiscussionReplyResponse]:
    """List replies for a discussion."""
    replies = await reply_crud.get_by_discussion(db, discussion_id=discussion_id)
    return [DiscussionReplyResponse.model_validate(r) for r in replies]


@router.post(
    "/{discussion_id}/replies",
    response_model=DiscussionReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create reply",
    description="Create a reply to a discussion",
)
async def create_reply(
    discussion_id: int,
    reply_in: DiscussionReplyCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DiscussionReplyResponse:
    """Create a reply."""
    discussion = await discussion_crud.get(db, discussion_id)
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다",
        )

    reply = await reply_crud.create_reply(
        db, discussion_id=discussion_id, user_id=current_user.id, obj_in=reply_in
    )

    # Update reply count
    await discussion_crud.update_reply_count(db, discussion_id=discussion_id)

    return DiscussionReplyResponse.model_validate(reply)


@router.patch(
    "/{discussion_id}/replies/{reply_id}",
    response_model=DiscussionReplyResponse,
    summary="Update reply",
    description="Update a reply (owner only)",
)
async def update_reply(
    discussion_id: int,
    reply_id: int,
    reply_in: DiscussionReplyUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DiscussionReplyResponse:
    """Update a reply."""
    reply = await reply_crud.get(db, reply_id)
    if not reply or reply.discussion_id != discussion_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다",
        )

    if reply.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="수정 권한이 없습니다",
        )

    reply = await reply_crud.update_reply(db, db_obj=reply, content=reply_in.content)
    return DiscussionReplyResponse.model_validate(reply)


@router.delete(
    "/{discussion_id}/replies/{reply_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete reply",
    description="Delete a reply (owner only)",
)
async def delete_reply(
    discussion_id: int,
    reply_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a reply."""
    reply = await reply_crud.get(db, reply_id)
    if not reply or reply.discussion_id != discussion_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다",
        )

    if reply.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="삭제 권한이 없습니다",
        )

    await reply_crud.delete(db, id=reply_id)
    await discussion_crud.update_reply_count(db, discussion_id=discussion_id)


@router.post(
    "/{discussion_id}/replies/{reply_id}/like",
    summary="Toggle reply like",
    description="Toggle like on a reply",
)
async def toggle_reply_like(
    discussion_id: int,
    reply_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Toggle like on a reply."""
    reply = await reply_crud.get(db, reply_id)
    if not reply or reply.discussion_id != discussion_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="댓글을 찾을 수 없습니다",
        )

    is_liked = await like_crud.toggle_like(
        db, user_id=current_user.id, reply_id=reply_id
    )
    return {"is_liked": is_liked}
