"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AdminUser, CurrentUserOptional
from app.crud.user import user as user_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.user import (
    UserCreate,
    UserMeResponse,
    UserQuery,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)

router = APIRouter()


@router.get(
    "/me",
    response_model=UserMeResponse | None,
    summary="Get current user",
    description="Get the currently logged-in user's information",
)
async def get_current_user_info(
    current_user: CurrentUserOptional,
) -> UserMeResponse | None:
    """Get current logged-in user."""
    if not current_user:
        return None
    return UserMeResponse.model_validate(current_user)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users",
    description="List all users with pagination and filtering (Admin only)",
)
async def list_users(
    query: UserQuery = Depends(),
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserResponse]:
    """List users with filtering and pagination."""
    users, total = await user_crud.get_multi_with_query(db, query=query)

    return PaginatedResponse(
        data=[UserResponse.model_validate(u) for u in users],
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get a specific user by ID (Admin only)",
)
async def get_user(
    user_id: str,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get a user by ID."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )
    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (Admin only)",
)
async def create_user(
    user_in: UserCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user."""
    existing = await user_crud.get_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다",
        )

    user = await user_crud.create_user(db, obj_in=user_in)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update a user's profile (Admin only)",
)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    user = await user_crud.update_user(db, db_obj=user, obj_in=user_in)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role",
    description="Update a user's role (Admin only)",
)
async def update_user_role(
    user_id: str,
    role_in: UserRoleUpdate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's role."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    user = await user_crud.update_role(db, db_obj=user, role=role_in.role.value)
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
    description="Deactivate a user account (Admin only)",
)
async def deactivate_user(
    user_id: str,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Deactivate a user."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    user = await user_crud.deactivate(db, db_obj=user)
    return UserResponse.model_validate(user)


@router.post(
    "/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
    description="Activate a user account (Admin only)",
)
async def activate_user(
    user_id: str,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Activate a user."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    user = await user_crud.activate(db, db_obj=user)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Permanently delete a user (Admin only)",
)
async def delete_user(
    user_id: str,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a user."""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다",
        )

    await user_crud.delete(db, id=user_id)
