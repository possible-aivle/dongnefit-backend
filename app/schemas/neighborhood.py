"""Neighborhood schemas."""

from pydantic import Field

from app.schemas.base import BaseSchema, PaginationParams, TimestampSchema


class Coordinates(BaseSchema):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


# === Request Schemas ===


class NeighborhoodCreate(BaseSchema):
    """Schema for creating a neighborhood."""

    name: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    coordinates: Coordinates | None = None
    description: str | None = None


class NeighborhoodUpdate(BaseSchema):
    """Schema for updating a neighborhood."""

    name: str | None = Field(None, min_length=1, max_length=100)
    district: str | None = Field(None, min_length=1, max_length=100)
    city: str | None = Field(None, min_length=1, max_length=100)
    coordinates: Coordinates | None = None
    description: str | None = None


class NeighborhoodQuery(PaginationParams):
    """Query parameters for listing neighborhoods."""

    search: str | None = None
    city: str | None = None
    district: str | None = None
    sort_by: str = "name"  # name, newest


class LocationQuery(BaseSchema):
    """Query for finding neighborhoods by location."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_km: float = Field(5.0, ge=0.1, le=50)


# === Response Schemas ===


class NeighborhoodResponse(TimestampSchema):
    """Neighborhood response."""

    id: int
    name: str
    district: str
    city: str
    coordinates: Coordinates | None
    description: str | None


class NeighborhoodSummary(BaseSchema):
    """Neighborhood summary for lists."""

    id: int
    name: str
    district: str
    city: str


class NeighborhoodWithStats(NeighborhoodResponse):
    """Neighborhood with additional statistics."""

    member_count: int = 0
    report_count: int = 0
    discussion_count: int = 0
