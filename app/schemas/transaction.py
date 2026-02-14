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
    raw_data: dict[str, Any] | None = None


class OfficialLandPriceRead(BaseSchema):
    """개별공시지가 조회 스키마."""

    id: int
    pnu: str
    base_year: int
    base_date: date | None
    price_per_sqm: int | None
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
