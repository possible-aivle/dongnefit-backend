"""Authentication dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user import user as user_crud
from app.database import get_db
from app.models.user import User, UserRole


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user from session if logged in, otherwise None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    user = await user_crud.get(db, user_id)
    if not user or not user.is_active:
        # Clear invalid session
        request.session.clear()
        return None

    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Get current user from session. Raises 401 if not logged in."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다",
        )
    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin role. Raises 403 if not admin."""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_admin)]
