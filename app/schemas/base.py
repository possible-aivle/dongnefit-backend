"""Base schemas and utilities."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel


def wkb_to_geojson(value: Any) -> dict[str, Any] | None:
    """WKBElement를 GeoJSON dict로 변환합니다.

    PostGIS Geometry 컬럼에서 읽은 WKBElement를
    API 응답용 GeoJSON dict로 변환합니다.

    사용 예:
        geojson = wkb_to_geojson(row.geometry)
        # {"type": "Polygon", "coordinates": [...]}
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value

    from geoalchemy2.elements import WKBElement
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping

    if isinstance(value, WKBElement):
        return mapping(to_shape(value))
    return None


def wkb_to_shapely(value: Any) -> Any:
    """WKBElement를 Shapely geometry 객체로 변환합니다.

    서비스 로직에서 공간 연산(contains, intersects, area 등)이
    필요할 때 사용합니다.

    사용 예:
        shape = wkb_to_shapely(row.geometry)
        area = shape.area
        centroid = shape.centroid
    """
    if value is None:
        return None

    from geoalchemy2.elements import WKBElement
    from geoalchemy2.shape import to_shape

    if isinstance(value, WKBElement):
        return to_shape(value)
    return value


# Pydantic 스키마에서 geometry 필드에 사용하는 타입.
# DB에서 읽은 WKBElement를 자동으로 GeoJSON dict로 변환합니다.
# 사용법: geometry: GeoJSON = None
GeoJSON = Annotated[dict[str, Any] | None, BeforeValidator(wkb_to_geojson)]


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination query parameters."""

    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseSchema):
    """Pagination metadata in response."""

    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseSchema):
    """Generic paginated response."""

    data: list[T]
    pagination: PaginationMeta
