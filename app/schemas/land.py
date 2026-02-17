"""토지 관련 스키마."""

from datetime import datetime

from app.schemas.base import BaseSchema


class LandCharacteristicCreate(BaseSchema):
    """토지특성 생성 스키마."""

    pnu: str
    jimok: str | None = None
    land_area: float | None = None
    use_zone: str | None = None
    land_use: str | None = None
    official_price: int | None = None



class LandCharacteristicRead(BaseSchema):
    """토지특성 조회 스키마."""

    id: int
    pnu: str
    jimok: str | None
    land_area: float | None
    use_zone: str | None
    land_use: str | None
    official_price: int | None


    created_at: datetime | None


class LandUsePlanCreate(BaseSchema):
    """토지이용계획 생성 스키마."""

    pnu: str
    use_district_name: str | None = None



class LandUsePlanRead(BaseSchema):
    """토지이용계획 조회 스키마."""

    id: int
    pnu: str
    use_district_name: str | None


    created_at: datetime | None


class LandAndForestInfoCreate(BaseSchema):
    """토지임야정보 생성 스키마."""

    pnu: str
    jimok: str | None = None
    area: float | None = None
    ownership: str | None = None
    owner_count: int | None = None



class LandAndForestInfoRead(BaseSchema):
    """토지임야정보 조회 스키마."""

    id: int
    pnu: str
    jimok: str | None
    area: float | None
    ownership: str | None
    owner_count: int | None


    created_at: datetime | None
