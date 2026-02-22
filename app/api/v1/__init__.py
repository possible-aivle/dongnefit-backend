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
# 로컬 전용 엔드포인트 (/api/v1/local/) — 실서버 DB 테이블 미사용
local_router = APIRouter()
local_router.include_router(lots.router, prefix="/lots", tags=["local-lots"])
local_router.include_router(buildings.router, prefix="/buildings", tags=["local-buildings"])
local_router.include_router(transactions.router, prefix="/transactions", tags=["local-transactions"])
local_router.include_router(properties.router, prefix="/properties", tags=["local-properties"])
local_router.include_router(map.router, prefix="/map", tags=["local-map"])
local_router.include_router(talk.router, tags=["local-talk"])
router.include_router(local_router, prefix="/local")
