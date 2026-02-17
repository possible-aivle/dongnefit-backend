"""필지(Lot) 모델 - PNU 기반 중심 테이블.

연속지적도 데이터로부터 생성되며 모든 공공데이터의 기준이 되는 테이블.
PNU(19자리): 시도(2) + 시군구(3) + 읍면동(3) + 리(2) + 산구분(1) + 본번(4) + 부번(4)

토지 관련 6개 테이블을 통합:
- land_characteristics (토지특성) → flat 컬럼
- land_and_forest_infos (토지임야) → flat 컬럼
- land_use_plans (토지이용계획) → JSONB
- land_ownerships (토지소유) → JSONB
- official_land_prices (공시지가) → JSONB
- building_register_ancillary_lots (부속지번) → JSONB
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import PublicDataBase, geometry_column, get_utc_now


# pnu 가 primary_key 여서 SQLModel 상속
class Lot(SQLModel, table=True):
    """필지 테이블 - 연속지적도 + 토지 통합.

    연속지적도가 기반 데이터로 가장 먼저 업데이트되어야 함.
    PNU가 없는 경우 새로 생성, 이미 있는 경우 기존 데이터 업데이트.
    """

    __tablename__ = "lots"

    pnu: str = Field(
        max_length=19,
        primary_key=True,
        description="필지고유번호",
    )
    geometry: Any = geometry_column(description="필지 경계 (Polygon/MultiPolygon)")
    created_at: datetime | None = Field(default_factory=get_utc_now)

    # ── flat 컬럼 (1:1 from 토지특성/토지임야) ──
    jimok: str | None = Field(default=None, max_length=20, description="지목명")
    jimok_code: str | None = Field(default=None, max_length=10, description="지목코드")
    area: float | None = Field(default=None, description="면적(㎡)")
    use_zone: str | None = Field(default=None, max_length=50, description="용도지역명")
    use_zone_code: str | None = Field(default=None, max_length=10, description="용도지역코드")
    land_use: str | None = Field(default=None, max_length=30, description="토지이용현황")
    land_use_code: str | None = Field(default=None, max_length=10, description="토지이용현황코드")
    official_price: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True),
        description="공시지가(원)",
    )
    ownership: str | None = Field(default=None, max_length=20, description="소유구분명")
    ownership_code: str | None = Field(default=None, max_length=10, description="소유구분코드")
    owner_count: int | None = Field(default=None, description="소유(공유)인수")

    # ── JSONB 컬럼 (1:N) ──
    use_plans: Any = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='토지이용계획 [{"use_district_name": "..."}]',
    )
    ownerships: Any = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='토지소유 [{"base_year_month", "co_owner_seq", ...}]',
    )
    official_prices: Any = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='공시지가 [{"base_year", "price_per_sqm"}]',
    )
    ancillary_lots: Any = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description='부속지번 [{"mgm_bldrgst_pk", "atch_pnu", "created_date"}]',
    )


class AncillaryLand(PublicDataBase, table=True):
    """부속필지 테이블.

    부속필지 데이터 업로드 → Lot 테이블 업데이트 기반 데이터.
    건축물대장 > 부속지번 데이터.
    """

    __tablename__ = "ancillary_lands"

    pnu: str = Field(
        max_length=19,
        # lots.pnu 참조: FK 대신 인덱스로 관리 (파이프라인 독립 적재 지원)
        description="필지고유번호",
        index=True,
    )
