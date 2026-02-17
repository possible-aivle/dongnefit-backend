"""필지 스키마."""

from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.schemas.base import BaseSchema, GeoJSON


class LotCreate(BaseSchema):
    """필지 생성 스키마."""

    pnu: str
    geometry: dict[str, Any] | None = None

    # flat 컬럼
    jimok: str | None = None
    jimok_code: str | None = None
    area: float | None = None
    use_zone: str | None = None
    use_zone_code: str | None = None
    land_use: str | None = None
    land_use_code: str | None = None
    official_price: int | None = None
    ownership: str | None = None
    ownership_code: str | None = None
    owner_count: int | None = None

    # JSONB 컬럼
    use_plans: list[dict[str, Any]] | None = None
    ownerships: list[dict[str, Any]] | None = None
    official_prices: list[dict[str, Any]] | None = None
    ancillary_lots: list[dict[str, Any]] | None = None

    @field_validator("pnu")
    @classmethod
    def validate_pnu(cls, v: str) -> str:
        if len(v) != 19 or not v.isdigit():
            raise ValueError("PNU는 19자리 숫자여야 합니다")
        return v


class LotRead(BaseSchema):
    """필지 조회 스키마."""

    pnu: str
    geometry: GeoJSON = None
    created_at: datetime | None = None

    # flat 컬럼
    jimok: str | None = None
    jimok_code: str | None = None
    area: float | None = None
    use_zone: str | None = None
    use_zone_code: str | None = None
    land_use: str | None = None
    land_use_code: str | None = None
    official_price: int | None = None
    ownership: str | None = None
    ownership_code: str | None = None
    owner_count: int | None = None

    # JSONB 컬럼
    use_plans: list[dict[str, Any]] | None = None
    ownerships: list[dict[str, Any]] | None = None
    official_prices: list[dict[str, Any]] | None = None
    ancillary_lots: list[dict[str, Any]] | None = None


class AncillaryLandCreate(BaseSchema):
    """부속필지 생성 스키마."""

    pnu: str



class AncillaryLandRead(BaseSchema):
    """부속필지 조회 스키마."""

    id: int
    pnu: str

    created_at: datetime | None
