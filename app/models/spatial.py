"""공간(GIS) 데이터 모델 (도로중심선, 용도지역지구)."""

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import PublicDataBase


class RoadCenterLine(PublicDataBase, table=True):
    """도로중심선 테이블.

    코어 데이터.
    vworld shp 데이터 기반.
    geometry는 raw_data JSONB에 GeoJSON 형태로 저장.
    추후 PostGIS 확장 시 geometry 컬럼으로 마이그레이션 가능.
    """

    __tablename__ = "road_center_lines"

    source_id: str = Field(
        max_length=200,
        index=True,
        description="원본 데이터 피처 ID",
    )
    road_name: str | None = Field(
        default=None,
        max_length=200,
        description="도로명",
    )
    admin_code: str | None = Field(
        default=None,
        max_length=10,
        index=True,
        description="관할 행정구역코드",
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry",
    )


class UseRegionDistrict(PublicDataBase, table=True):
    """용도지역지구 테이블.

    코어 데이터.
    vworld shp 데이터 기반.
    geometry는 raw_data JSONB에 GeoJSON 형태로 저장.
    """

    __tablename__ = "use_region_districts"

    source_id: str = Field(
        max_length=200,
        index=True,
        description="원본 데이터 피처 ID",
    )
    district_name: str | None = Field(
        default=None,
        max_length=200,
        description="용도지역/지구/구역명",
    )
    district_code: str | None = Field(
        default=None,
        max_length=50,
        description="용도지역/지구/구역코드",
    )
    admin_code: str | None = Field(
        default=None,
        max_length=10,
        index=True,
        description="관할 행정구역코드",
    )
    geometry: dict | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="GeoJSON geometry",
    )
