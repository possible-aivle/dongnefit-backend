"""필지 스키마."""

from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.schemas.base import BaseSchema, GeoJSON


class LotCreate(BaseSchema):
    """필지 생성 스키마."""

    pnu: str
    address: str | None = None
    geometry: dict[str, Any] | None = None

    # flat 컬럼
    jimok: str | None = None
    area: float | None = None
    use_zone: str | None = None
    land_use: str | None = None
    official_price: int | None = None
    ownership: str | None = None
    owner_count: int | None = None

    # JSONB 컬럼
    use_plans: list[dict[str, Any]] | None = None
    official_prices: list[dict[str, Any]] | None = None
    ancillary_lots: list[dict[str, Any]] | None = None

    @field_validator("pnu")
    @classmethod
    def validate_pnu(cls, v: str) -> str:
        if len(v) != 19 or not v.isdigit():
            raise ValueError("PNU는 19자리 숫자여야 합니다")
        return v


class LotFilterOptions(BaseSchema):
    """필터 옵션 응답 스키마."""

    jimok: list[str] = []
    ownership: list[str] = []
    use_zone: list[str] = []
    land_use: list[str] = []


class LotRead(BaseSchema):
    """필지 조회 스키마."""

    pnu: str
    address: str | None = None
    geometry: GeoJSON = None
    created_at: datetime | None = None

    # flat 컬럼
    jimok: str | None = None
    area: float | None = None
    use_zone: str | None = None
    land_use: str | None = None
    official_price: int | None = None
    ownership: str | None = None
    owner_count: int | None = None

    # JSONB 컬럼
    use_plans: list[dict[str, Any]] | None = None
    official_prices: list[dict[str, Any]] | None = None
    ancillary_lots: list[dict[str, Any]] | None = None


