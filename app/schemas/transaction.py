"""실거래가(매매/전월세) 스키마."""

from datetime import date, datetime

from app.models.enums import PropertyType, TransactionType
from app.schemas.base import BaseSchema


class RealEstateSaleCreate(BaseSchema):
    """부동산 매매 실거래가 생성 스키마."""

    property_type: PropertyType
    transaction_date: date | None = None
    transaction_amount: int | None = None



class RealEstateSaleRead(BaseSchema):
    """부동산 매매 실거래가 조회 스키마."""

    id: int
    property_type: PropertyType
    transaction_date: date | None
    transaction_amount: int | None

    created_at: datetime | None


class RealEstateRentalCreate(BaseSchema):
    """부동산 전월세 실거래가 생성 스키마."""

    property_type: PropertyType
    transaction_type: TransactionType
    transaction_date: date | None = None
    deposit: int | None = None
    monthly_rent_amount: int | None = None



class RealEstateRentalRead(BaseSchema):
    """부동산 전월세 실거래가 조회 스키마."""

    id: int
    property_type: PropertyType
    transaction_type: TransactionType
    transaction_date: date | None
    deposit: int | None
    monthly_rent_amount: int | None


    created_at: datetime | None
