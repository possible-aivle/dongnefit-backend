"""토지소유정보 스키마."""

from datetime import datetime
from typing import Any

from app.schemas.base import BaseSchema


class LandOwnershipCreate(BaseSchema):
    """토지소유정보 생성 스키마."""

    pnu: str
    base_year_month: str
    co_owner_seq: str
    ownership_type: str | None = None
    ownership_change_reason: str | None = None
    ownership_change_date: str | None = None
    owner_count: int | None = None
    raw_data: dict[str, Any] | None = None


class LandOwnershipRead(BaseSchema):
    """토지소유정보 조회 스키마."""

    id: int
    pnu: str
    base_year_month: str
    co_owner_seq: str
    ownership_type: str | None
    ownership_change_reason: str | None
    ownership_change_date: str | None
    owner_count: int | None
    raw_data: dict[str, Any] | None
    collected_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
