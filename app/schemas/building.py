"""건물 관련 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema, GeoJSON


class BuildingRegisterHeaderCreate(BaseSchema):
    """건축물대장 표제부 생성 스키마."""

    pnu: str



class BuildingRegisterHeaderRead(BaseSchema):
    """건축물대장 표제부 조회 스키마."""

    id: int
    pnu: str


    created_at: datetime | None


class BuildingRegisterFloorDetailCreate(BaseSchema):
    """건축물대장 층별개요 생성 스키마."""

    pnu: str



class BuildingRegisterFloorDetailRead(BaseSchema):
    """건축물대장 층별개요 조회 스키마."""

    id: int
    pnu: str


    created_at: datetime | None


class BuildingRegisterGeneralCreate(BaseSchema):
    """건축물대장 총괄표제부 생성 스키마."""

    pnu: str



class BuildingRegisterGeneralRead(BaseSchema):
    """건축물대장 총괄표제부 조회 스키마."""

    id: int
    pnu: str


    created_at: datetime | None


class BuildingRegisterAreaCreate(BaseSchema):
    """건축물대장 전유공용면적 생성 스키마."""

    pnu: str



class BuildingRegisterAreaRead(BaseSchema):
    """건축물대장 전유공용면적 조회 스키마."""

    id: int
    pnu: str


    created_at: datetime | None


class GisBuildingIntegratedCreate(BaseSchema):
    """GIS건물통합정보 생성 스키마."""

    pnu: str
    use_name: str | None = None
    building_area: float | None = None
    approval_date: str | None = None
    total_floor_area: float | None = None
    site_area: float | None = None
    height: float | None = None
    building_id: str | None = None
    building_name: str | None = None
    above_ground_floors: int | None = None
    underground_floors: int | None = None
    geometry: dict[str, Any] | None = None



class GisBuildingIntegratedRead(BaseSchema):
    """GIS건물통합정보 조회 스키마."""

    id: int
    pnu: str
    use_name: str | None
    building_area: float | None
    approval_date: str | None
    total_floor_area: float | None
    site_area: float | None
    height: float | None
    building_id: str | None
    building_name: str | None
    above_ground_floors: int | None
    underground_floors: int | None
    geometry: GeoJSON = None


    created_at: datetime | None
