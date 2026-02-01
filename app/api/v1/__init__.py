"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import content, map

router = APIRouter()

router.include_router(map.router, prefix="/map", tags=["map"])
router.include_router(content.router, prefix="/content", tags=["content"])
