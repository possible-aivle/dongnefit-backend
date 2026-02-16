"""행정구역 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema, GeoJSON


class AdministrativeDivisionCreate(BaseSchema):
    """행정구역(시도/시군구) 생성 스키마."""

    code: str
    name: str
    level: int
    parent_code: str | None = None
    geometry: dict[str, Any] | None = None



class AdministrativeDivisionRead(BaseSchema):
    """행정구역(시도/시군구) 조회 스키마."""

    id: int
    code: str
    name: str
    level: int
    parent_code: str | None
    geometry: GeoJSON = None

    created_at: datetime | None
    updated_at: datetime | None


class AdministrativeEmdCreate(BaseSchema):
    """행정구역 읍면동 생성 스키마."""

    code: str
    name: str
    division_code: str
    geometry: dict[str, Any] | None = None



class AdministrativeEmdRead(BaseSchema):
    """행정구역 읍면동 조회 스키마."""

    id: int
    code: str
    name: str
    division_code: str
    geometry: GeoJSON = None

    created_at: datetime | None
    updated_at: datetime | None
