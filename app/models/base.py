"""Base model mixins."""

from datetime import UTC, datetime
from typing import Any

from geoalchemy2 import Geometry as GeoAlchemyGeometry
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def get_utc_now() -> datetime:
    """Get current UTC time (naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


def geometry_column(
    geometry_type: str = "GEOMETRY",
    srid: int = 4326,
    description: str = "PostGIS Geometry",
) -> Any:
    """PostGIS Geometry 컬럼 필드를 생성합니다.

    DB에서 읽을 때 WKBElement로 반환되며,
    Shapely 변환: `geoalchemy2.shape.to_shape(wkb_element)`
    GeoJSON 변환: `shapely.geometry.mapping(to_shape(wkb_element))`

    파이프라인에서 쓸 때는 WKT 문자열을 전달하고
    loader에서 ST_GeomFromText()로 변환합니다.
    """
    return Field(
        default=None,
        sa_column=Column(
            GeoAlchemyGeometry(
                geometry_type=geometry_type,
                srid=srid,
                spatial_index=True,
            ),
            nullable=True,
        ),
        description=description,
    )


class TimestampMixin(SQLModel):
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)


class PublicDataBase(SQLModel):
    """공공데이터 공통 필드 믹스인.

    모든 공공데이터 테이블이 상속받는 베이스.
    raw_data JSONB로 원본 데이터를 보관하여 추후 컬럼 확장 시 재처리 가능.
    """

    id: int | None = Field(default=None, primary_key=True)
    raw_data: dict | None = Field(
        default=None,
        sa_type=JSONB,
        description="원본 데이터 (전처리 전 원본 보관)",
    )
    created_at: datetime | None = Field(default_factory=get_utc_now)
    updated_at: datetime | None = Field(default_factory=get_utc_now)
