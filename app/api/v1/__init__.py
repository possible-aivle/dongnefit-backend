"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    discussions,
    neighborhoods,
    notifications,
    reports,
    users,
)

router = APIRouter()

router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(neighborhoods.router, prefix="/neighborhoods", tags=["neighborhoods"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(discussions.router, prefix="/discussions", tags=["discussions"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
