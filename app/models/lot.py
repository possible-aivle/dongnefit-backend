"""필지(Lot) 모델 - PNU 기반 중심 테이블.

연속지적도 데이터로부터 생성되며 모든 공공데이터의 기준이 되는 테이블.
PNU(19자리): 시도(2) + 시군구(3) + 읍면동(3) + 리(2) + 산구분(1) + 본번(4) + 부번(4)
"""

from datetime import datetime

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.base import PublicDataBase, get_utc_now


# pnu 가 primary_key 여서 SQLModel 상속
class Lot(SQLModel, table=True):
    """필지 테이블 - 연속지적도 기반.

    연속지적도가 기반 데이터로 가장 먼저 업데이트되어야 함.
    PNU가 없는 경우 새로 생성, 이미 있는 경우 기존 데이터 업데이트.
    """

    __tablename__ = "lots"

    pnu: str = Field(
        max_length=19,
        primary_key=True,
        description="필지고유번호 (19자리)",
    )
    sido_code: str = Field(
        max_length=2,
        index=True,
        description="시도코드 (2자리)",
    )
    sgg_code: str = Field(
        max_length=5,
        index=True,
        description="시군구코드 (5자리: 시도+시군구)",
    )
    emd_code: str = Field(
        max_length=8,
        index=True,
        description="읍면동코드 (8자리: 시도+시군구+읍면동)",
    )
    jibun_address: str | None = Field(
        default=None,
        sa_column=Column(String(500)),
        description="지번주소",
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry (Polygon/MultiPolygon)",
    )
    collected_at: datetime = Field(default_factory=get_utc_now)
    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)


class AncillaryLand(PublicDataBase, table=True):
    """부속필지 테이블.

    부속필지 데이터 업로드 → Lot 테이블 업데이트 기반 데이터.
    건축물대장 > 부속지번 데이터.
    """

    __tablename__ = "ancillary_lands"

    pnu: str = Field(
        max_length=19,
        foreign_key="lots.pnu",
        index=True,
        description="필지고유번호",
    )
