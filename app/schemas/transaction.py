"""실거래가 및 공시지가 스키마."""

from datetime import date, datetime
from typing import Any

from app.models.enums import PropertyType, TransactionType
from app.schemas.base import BaseSchema


class OfficialLandPriceCreate(BaseSchema):
    """개별공시지가 생성 스키마."""

    pnu: str
    base_year: int
    base_date: date | None = None
    price_per_sqm: int | None = None
    bjd_code: str | None = None
    jibun: str | None = None
    base_month: int | None = None
    is_standard: bool | None = None
    data_base_date: str | None = None
    raw_data: dict[str, Any] | None = None


class OfficialLandPriceRead(BaseSchema):
    """개별공시지가 조회 스키마."""

    id: int
    pnu: str
    base_year: int
    base_date: date | None
    price_per_sqm: int | None
    bjd_code: str | None
    jibun: str | None
    base_month: int | None
    is_standard: bool | None
    data_base_date: str | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class StandardLandPriceCreate(BaseSchema):
    """표준지공시지가 생성 스키마."""

    pnu: str
    base_year: int
    bjd_code: str | None = None
    jibun: str | None = None
    jimok_code: str | None = None
    jimok_name: str | None = None
    land_area: float | None = None
    use_zone_code: str | None = None
    use_zone_name: str | None = None
    land_use_code: str | None = None
    land_use_name: str | None = None
    official_price: int | None = None
    data_base_date: str | None = None
    raw_data: dict[str, Any] | None = None


class StandardLandPriceRead(BaseSchema):
    """표준지공시지가 조회 스키마."""

    id: int
    pnu: str
    base_year: int
    bjd_code: str | None
    jibun: str | None
    jimok_code: str | None
    jimok_name: str | None
    land_area: float | None
    use_zone_code: str | None
    use_zone_name: str | None
    land_use_code: str | None
    land_use_name: str | None
    official_price: int | None
    data_base_date: str | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class RealEstateTransactionCreate(BaseSchema):
    """부동산 실거래가 생성 스키마."""

    pnu: str | None = None
    property_type: PropertyType
    transaction_type: TransactionType
    transaction_date: date | None = None
    transaction_amount: int | None = None
    raw_data: dict[str, Any] | None = None


class RealEstateTransactionRead(BaseSchema):
    """부동산 실거래가 조회 스키마."""

    id: int
    pnu: str | None
    property_type: PropertyType
    transaction_type: TransactionType
    transaction_date: date | None
    transaction_amount: int | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
