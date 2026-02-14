"""건물 관련 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class BuildingRegisterHeaderCreate(BaseSchema):
    """건축물대장 표제부 생성 스키마."""

    pnu: str
    raw_data: dict[str, Any] | None = None


class BuildingRegisterHeaderRead(BaseSchema):
    """건축물대장 표제부 조회 스키마."""

    id: int
    pnu: str
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class BuildingRegisterFloorDetailCreate(BaseSchema):
    """건축물대장 층별개요 생성 스키마."""

    pnu: str
    raw_data: dict[str, Any] | None = None


class BuildingRegisterFloorDetailRead(BaseSchema):
    """건축물대장 층별개요 조회 스키마."""

    id: int
    pnu: str
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
