"""User schemas."""

from datetime import datetime
from enum import Enum

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"


class AuthProvider(Enum):
    GOOGLE = "google"
    KAKAO = "kakao"


# === Request Schemas ===


class UserCreate(BaseSchema):
    """Schema for creating a user (admin only)."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    profile_image_url: str | None = None
    role: UserRole = UserRole.USER
    provider: AuthProvider
    phone: str | None = None


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    name: str | None = Field(None, min_length=1, max_length=100)
    profile_image_url: str | None = None
    phone: str | None = None


class UserRoleUpdate(BaseSchema):
    """Schema for updating user role (admin only)."""

    role: UserRole


class UserQuery(PaginationParams):
    """Query parameters for listing users."""

    search: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    provider: AuthProvider | None = None
    sort_by: str = "newest"  # newest, oldest, name


# === Response Schemas ===


class UserPublic(BaseSchema):
    """Public user information."""

    id: str
    name: str
    profile_image_url: str | None
    role: UserRole


class UserResponse(TimestampSchema):
    """Full user response."""

    id: str
    email: str
    name: str
    profile_image_url: str | None
    role: UserRole
    provider: AuthProvider
    is_active: bool
    phone: str | None
    last_login_at: datetime | None


class UserMeResponse(UserResponse):
    """Current user response with additional info."""

    customer_key: str | None = None
