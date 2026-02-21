"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    buildings,
    discussions,
    lots,
    map,
    neighborhoods,
    notifications,
    properties,
    reports,
    talk,
    transactions,
    users,
)

router = APIRouter()

router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(neighborhoods.router, prefix="/neighborhoods", tags=["neighborhoods"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(discussions.router, prefix="/discussions", tags=["discussions"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(talk.router, tags=["talk"])

# 공공데이터 엔드포인트
router.include_router(lots.router, prefix="/lots", tags=["lots"])
router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(map.router, prefix="/map", tags=["map"])
