"""Notification endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AdminUser, CurrentUser
from app.crud.notification import notification as notification_crud
from app.crud.notification import notification_settings as settings_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.notification import (
    NotificationCreate,
    NotificationQuery,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    UnreadCountResponse,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List notifications",
    description="Get current user's notifications",
)
async def list_notifications(
    query: NotificationQuery = Depends(),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[NotificationResponse]:
    """List current user's notifications."""
    notifications, total = await notification_crud.get_user_notifications(
        db, user_id=current_user.id, query=query
    )

    return PaginatedResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread count",
    description="Get unread notification count",
)
async def get_unread_count(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    """Get unread notification count."""
    count = await notification_crud.get_unread_count(db, user_id=current_user.id)
    return UnreadCountResponse(count=count)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Get settings",
    description="Get notification settings",
)
async def get_settings(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    """Get notification settings."""
    settings = await settings_crud.get_or_create(db, user_id=current_user.id)
    return NotificationSettingsResponse.model_validate(settings)


@router.patch(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Update settings",
    description="Update notification settings",
)
async def update_settings(
    settings_in: NotificationSettingsUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    """Update notification settings."""
    settings = await settings_crud.get_or_create(db, user_id=current_user.id)
    settings = await settings_crud.update_settings(
        db, db_obj=settings, obj_in=settings_in
    )
    return NotificationSettingsResponse.model_validate(settings)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get notification",
    description="Get a specific notification",
)
async def get_notification(
    notification_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Get a notification by ID."""
    notification = await notification_crud.get(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다",
        )
    return NotificationResponse.model_validate(notification)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark as read",
    description="Mark a notification as read",
)
async def mark_as_read(
    notification_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    notification = await notification_crud.get(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다",
        )

    notification = await notification_crud.mark_as_read(db, db_obj=notification)
    return NotificationResponse.model_validate(notification)


@router.post(
    "/read-all",
    summary="Mark all as read",
    description="Mark all notifications as read",
)
async def mark_all_as_read(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark all notifications as read."""
    count = await notification_crud.mark_all_as_read(db, user_id=current_user.id)
    return {"marked_count": count}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Delete a notification",
)
async def delete_notification(
    notification_id: int,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification."""
    notification = await notification_crud.get(db, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다",
        )

    await notification_crud.delete(db, id=notification_id)


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification",
    description="Create a notification (Admin only)",
)
async def create_notification(
    notification_in: NotificationCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Create a notification (admin/system)."""
    notification = await notification_crud.create_notification(db, obj_in=notification_in)
    return NotificationResponse.model_validate(notification)
