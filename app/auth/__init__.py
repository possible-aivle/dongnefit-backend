"""Authentication module."""

from app.auth.deps import get_current_user, get_current_user_optional, require_admin
from app.auth.oauth import oauth_router

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "oauth_router",
]
