"""공간(GIS) 데이터 모델 (도로중심선, 용도지역지구)."""

from typing import Any

from sqlmodel import Field

from app.models.base import PublicDataBase, geometry_column


class RoadCenterLine(PublicDataBase, table=True):
    """도로중심선 테이블.

    코어 데이터.
    vworld shp 데이터 기반.
    geometry는 PostGIS Geometry 컬럼으로 저장 (SRID=4326).
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
    geometry: Any = geometry_column(description="도로중심선 (LineString/MultiLineString)")


class UseRegionDistrict(PublicDataBase, table=True):
    """용도지역지구 테이블.

    코어 데이터.
    vworld shp 데이터 기반.
    geometry는 PostGIS Geometry 컬럼으로 저장 (SRID=4326).
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
    geometry: Any = geometry_column(description="용도지역지구 경계 (Polygon/MultiPolygon)")
