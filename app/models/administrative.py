"""행정구역 모델."""

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import PublicDataBase


class AdministrativeDivision(PublicDataBase, table=True):
    """행정구역 (시도/시군구) 테이블.

    행정구역 shp 데이터 기반.
    """

    __tablename__ = "administrative_divisions"

    code: str = Field(
        max_length=5,
        unique=True,
        index=True,
        description="행정구역코드 (시도 2자리, 시군구 5자리)",
    )
    name: str = Field(max_length=100, description="행정구역명")
    level: int = Field(description="행정구역 레벨 (1=시도, 2=시군구)")
    parent_code: str | None = Field(
        default=None,
        max_length=5,
        description="상위 행정구역코드 (시군구의 경우 시도코드)",
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry (Polygon/MultiPolygon)",
    )


class AdministrativeEmd(PublicDataBase, table=True):
    """행정구역 읍면동 테이블.

    행정구역 읍면동 shp 데이터 기반.
    서브 데이터로 분류됨.
    """

    __tablename__ = "administrative_emds"

    code: str = Field(
        max_length=10,
        unique=True,
        index=True,
        description="읍면동코드 (8~10자리)",
    )
    name: str = Field(max_length=100, description="읍면동명")
    division_code: str = Field(
        max_length=5,
        foreign_key="administrative_divisions.code",
        index=True,
        description="소속 시군구코드",
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry (Polygon/MultiPolygon)",
    )
