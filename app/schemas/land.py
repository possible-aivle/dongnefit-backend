"""토지 관련 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class LandCharacteristicCreate(BaseSchema):
    """토지특성 생성 스키마."""

    pnu: str
    data_year: int
    bjd_code: str | None = None
    jibun: str | None = None
    jimok_code: str | None = None
    jimok_name: str | None = None
    land_area: float | None = None
    use_zone_code: str | None = None
    use_zone_name: str | None = None
    land_use_code: str | None = None
    land_use_name: str | None = None
    road_side_code: str | None = None
    official_price: int | None = None
    data_base_date: str | None = None
    raw_data: dict[str, Any] | None = None


class LandCharacteristicRead(BaseSchema):
    """토지특성 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    bjd_code: str | None
    jibun: str | None
    jimok_code: str | None
    jimok_name: str | None
    land_area: float | None
    use_zone_code: str | None
    use_zone_name: str | None
    land_use_code: str | None
    land_use_name: str | None
    road_side_code: str | None
    official_price: int | None
    data_base_date: str | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class LandUsePlanCreate(BaseSchema):
    """토지이용계획 생성 스키마."""

    pnu: str
    data_year: int
    bjd_code: str | None = None
    jibun: str | None = None
    use_district_code: str | None = None
    use_district_name: str | None = None
    inclusion_code: str | None = None
    data_base_date: str | None = None
    raw_data: dict[str, Any] | None = None


class LandUsePlanRead(BaseSchema):
    """토지이용계획 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    bjd_code: str | None
    jibun: str | None
    use_district_code: str | None
    use_district_name: str | None
    inclusion_code: str | None
    data_base_date: str | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class LandAndForestInfoCreate(BaseSchema):
    """토지임야정보 생성 스키마."""

    pnu: str
    data_year: int
    bjd_code: str | None = None
    jibun: str | None = None
    jimok_code: str | None = None
    jimok_name: str | None = None
    area: float | None = None
    ownership_code: str | None = None
    ownership_name: str | None = None
    owner_count: int | None = None
    data_base_date: str | None = None
    raw_data: dict[str, Any] | None = None


class LandAndForestInfoRead(BaseSchema):
    """토지임야정보 조회 스키마."""

    id: int
    pnu: str
    data_year: int
    bjd_code: str | None
    jibun: str | None
    jimok_code: str | None
    jimok_name: str | None
    area: float | None
    ownership_code: str | None
    ownership_name: str | None
    owner_count: int | None
    data_base_date: str | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
