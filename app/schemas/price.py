"""주택가격 관련 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class IndividualHousePriceCreate(BaseSchema):
    """개별주택가격 생성 스키마."""

    pnu: str
    base_year: int
    house_price: int | None = None
    raw_data: dict[str, Any] | None = None


class IndividualHousePriceRead(BaseSchema):
    """개별주택가격 조회 스키마."""

    id: int
    pnu: str
    base_year: int
    house_price: int | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class ApartmentPriceCreate(BaseSchema):
    """공동주택가격 생성 스키마."""

    pnu: str
    base_year: int
    apt_type_name: str | None = None
    apt_name: str | None = None
    dong_name: str | None = None
    ho_name: str | None = None
    exclusive_area: float | None = None
    official_price: int | None = None
    raw_data: dict[str, Any] | None = None


class ApartmentPriceRead(BaseSchema):
    """공동주택가격 조회 스키마."""

    id: int
    pnu: str
    base_year: int
    apt_type_name: str | None
    apt_name: str | None
    dong_name: str | None
    ho_name: str | None
    exclusive_area: float | None
    official_price: int | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
