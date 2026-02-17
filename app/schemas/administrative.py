"""행정경계 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema, GeoJSON


class AdministrativeSidoCreate(BaseSchema):
    """행정경계 시도 생성 스키마."""

    sido_code: str
    name: str
    geometry: dict[str, Any] | None = None


class AdministrativeSidoRead(BaseSchema):
    """행정경계 시도 조회 스키마."""

    id: int
    sido_code: str
    name: str
    geometry: GeoJSON = None

    created_at: datetime | None


class AdministrativeSggCreate(BaseSchema):
    """행정경계 시군구 생성 스키마."""

    sgg_code: str
    name: str
    sido_code: str
    geometry: dict[str, Any] | None = None


class AdministrativeSggRead(BaseSchema):
    """행정경계 시군구 조회 스키마."""

    id: int
    sgg_code: str
    name: str
    sido_code: str
    geometry: GeoJSON = None

    created_at: datetime | None


class AdministrativeEmdCreate(BaseSchema):
    """행정경계 읍면동 생성 스키마."""

    emd_code: str
    name: str
    sgg_code: str
    geometry: dict[str, Any] | None = None


class AdministrativeEmdRead(BaseSchema):
    """행정경계 읍면동 조회 스키마."""

    id: int
    emd_code: str
    name: str
    sgg_code: str
    geometry: GeoJSON = None

    created_at: datetime | None
