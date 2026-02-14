"""토지 관련 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class LandCharacteristicCreate(BaseSchema):
    """토지특성 생성 스키마."""

    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None = None


class LandCharacteristicRead(BaseSchema):
    """토지특성 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class LandUsePlanCreate(BaseSchema):
    """토지이용계획 생성 스키마."""

    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None = None


class LandUsePlanRead(BaseSchema):
    """토지이용계획 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class LandAndForestInfoCreate(BaseSchema):
    """토지임야정보 생성 스키마."""

    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None = None


class LandAndForestInfoRead(BaseSchema):
    """토지임야정보 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
