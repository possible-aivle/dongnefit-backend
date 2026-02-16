"""공간(GIS) 데이터 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema, GeoJSON


class RoadCenterLineCreate(BaseSchema):
    """도로중심선 생성 스키마."""

    source_id: str
    road_name: str | None = None
    admin_code: str | None = None
    geometry: dict[str, Any] | None = None



class RoadCenterLineRead(BaseSchema):
    """도로중심선 조회 스키마."""

    id: int
    source_id: str
    road_name: str | None
    admin_code: str | None
    geometry: GeoJSON = None


    created_at: datetime | None


class UseRegionDistrictCreate(BaseSchema):
    """용도지역지구 생성 스키마."""

    source_id: str
    district_name: str | None = None
    district_code: str | None = None
    admin_code: str | None = None
    geometry: dict[str, Any] | None = None



class UseRegionDistrictRead(BaseSchema):
    """용도지역지구 조회 스키마."""

    id: int
    source_id: str
    district_name: str | None
    district_code: str | None
    admin_code: str | None
    geometry: GeoJSON = None


    created_at: datetime | None
