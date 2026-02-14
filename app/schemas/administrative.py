"""행정구역 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class AdministrativeDivisionCreate(BaseSchema):
    """행정구역(시도/시군구) 생성 스키마."""

    code: str
    name: str
    level: int
    parent_code: str | None = None
    raw_data: dict[str, Any] | None = None


class AdministrativeDivisionRead(BaseSchema):
    """행정구역(시도/시군구) 조회 스키마."""

    id: int
    code: str
    name: str
    level: int
    parent_code: str | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class AdministrativeEmdCreate(BaseSchema):
    """행정구역 읍면동 생성 스키마."""

    code: str
    name: str
    division_code: str
    raw_data: dict[str, Any] | None = None


class AdministrativeEmdRead(BaseSchema):
    """행정구역 읍면동 조회 스키마."""

    id: int
    code: str
    name: str
    division_code: str
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
