"""User model for authentication and profile."""

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin


class UserRole(Enum):
    """User role enum."""

    USER = "user"
    ADMIN = "admin"


class AuthProvider(Enum):
    """OAuth provider enum."""

    GOOGLE = "google"
    KAKAO = "kakao"


class User(TimestampMixin, table=True):
    """User model for OAuth authentication."""

    __tablename__ = "users"

    id: str = Field(primary_key=True, max_length=255)  # OAuth ID like "kakao:12345"
    email: str = Field(unique=True, max_length=255, index=True)
    name: str = Field(max_length=100)
    profile_image_url: str | None = Field(default=None, max_length=500)
    role: str = Field(default=UserRole.USER.value, max_length=20)
    provider: str = Field(max_length=20)
    is_active: bool = Field(default=True)
    password: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    customer_key: str | None = Field(default=None, max_length=255)
    last_login_at: datetime | None = Field(default=None)
