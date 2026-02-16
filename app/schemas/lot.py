"""필지 스키마."""

from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.schemas.base import BaseSchema, GeoJSON


class LotCreate(BaseSchema):
    """필지 생성 스키마."""

    pnu: str
    sido_code: str
    sgg_code: str
    emd_code: str
    jibun_address: str | None = None
    geometry: dict[str, Any] | None = None

    @field_validator("pnu")
    @classmethod
    def validate_pnu(cls, v: str) -> str:
        if len(v) != 19 or not v.isdigit():
            raise ValueError("PNU는 19자리 숫자여야 합니다")
        return v


class LotRead(BaseSchema):
    """필지 조회 스키마."""

    pnu: str
    sido_code: str
    sgg_code: str
    emd_code: str
    jibun_address: str | None
    geometry: GeoJSON = None
    created_at: datetime | None
    updated_at: datetime | None


class AncillaryLandCreate(BaseSchema):
    """부속필지 생성 스키마."""

    pnu: str



class AncillaryLandRead(BaseSchema):
    """부속필지 조회 스키마."""

    id: int
    pnu: str

    created_at: datetime | None
    updated_at: datetime | None
