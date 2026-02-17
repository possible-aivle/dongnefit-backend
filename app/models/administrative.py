"""행정경계 모델."""

from typing import Any

from sqlmodel import Field

from app.models.base import PublicDataBase, geometry_column


class AdministrativeSido(PublicDataBase, table=True):
    """행정경계 시도 테이블.

    행정경계 시도 SHP 데이터 기반.
    """

    __tablename__ = "administrative_sidos"

    sido_code: str = Field(
        max_length=2,
        unique=True,
        index=True,
        description="시도코드 (2자리)",
    )
    name: str = Field(max_length=100, description="시도명")
    geometry: Any = geometry_column(description="시도 경계 (Polygon/MultiPolygon)")


class AdministrativeSgg(PublicDataBase, table=True):
    """행정경계 시군구 테이블.

    행정경계 시군구 SHP 데이터 기반.
    """

    __tablename__ = "administrative_sggs"

    sgg_code: str = Field(
        max_length=5,
        unique=True,
        index=True,
        description="시군구코드 (5자리)",
    )
    name: str = Field(max_length=100, description="시군구명")
    sido_code: str = Field(
        max_length=2,
        index=True,
        description="소속 시도코드 (2자리)",
    )
    geometry: Any = geometry_column(description="시군구 경계 (Polygon/MultiPolygon)")


class AdministrativeEmd(PublicDataBase, table=True):
    """행정경계 읍면동 테이블.

    행정경계 읍면동 shp 데이터 기반.
    서브 데이터로 분류됨.
    """

    __tablename__ = "administrative_emds"

    emd_code: str = Field(
        max_length=10,
        unique=True,
        index=True,
        description="읍면동코드 (8~10자리)",
    )
    name: str = Field(max_length=100, description="읍면동명")
    sgg_code: str = Field(
        max_length=5,
        foreign_key="administrative_sggs.sgg_code",
        index=True,
        description="소속 시군구코드",
    )
    geometry: Any = geometry_column(description="읍면동 경계 (Polygon/MultiPolygon)")
