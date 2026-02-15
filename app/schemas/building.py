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


class GisBuildingIntegratedCreate(BaseSchema):
    """GIS건물통합정보 생성 스키마."""

    pnu: str
    bjd_code: str | None = None
    bjd_name: str | None = None
    jibun: str | None = None
    special_land_name: str | None = None
    use_name: str | None = None
    structure_name: str | None = None
    building_area: float | None = None
    approval_date: str | None = None
    total_floor_area: float | None = None
    site_area: float | None = None
    height: float | None = None
    building_coverage_ratio: float | None = None
    floor_area_ratio: float | None = None
    building_id: str | None = None
    is_violation: str | None = None
    data_base_date: str | None = None
    building_name: str | None = None
    building_dong_name: str | None = None
    above_ground_floors: int | None = None
    underground_floors: int | None = None
    data_change_date: str | None = None
    geometry: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None


class GisBuildingIntegratedRead(BaseSchema):
    """GIS건물통합정보 조회 스키마."""

    id: int
    pnu: str
    bjd_code: str | None
    bjd_name: str | None
    jibun: str | None
    special_land_name: str | None
    use_name: str | None
    structure_name: str | None
    building_area: float | None
    approval_date: str | None
    total_floor_area: float | None
    site_area: float | None
    height: float | None
    building_coverage_ratio: float | None
    floor_area_ratio: float | None
    building_id: str | None
    is_violation: str | None
    data_base_date: str | None
    building_name: str | None
    building_dong_name: str | None
    above_ground_floors: int | None
    underground_floors: int | None
    data_change_date: str | None
    geometry: dict[str, Any] | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
