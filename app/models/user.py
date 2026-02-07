"""User model for authentication and profile."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class UserRole(Enum):
    """User role enum."""

    USER = "user"
    ADMIN = "admin"


class AuthProvider(Enum):
    """OAuth provider enum."""

    GOOGLE = "google"
    KAKAO = "kakao"


class User(Base, TimestampMixin):
    """User model for OAuth authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # OAuth ID like "kakao:12345"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.USER.value, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # TODO: 빌링키로 나중에 구현
    last_login_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)
