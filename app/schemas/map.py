"""Map service schemas."""

from pydantic import Field

from app.schemas.base import BaseSchema


class LocationSearch(BaseSchema):
    """Location search request."""

    query: str = Field(..., description="Search query (address or keyword)")


class Coordinates(BaseSchema):
    """Geographic coordinates."""

    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class LocationResult(BaseSchema):
    """Single location result."""

    address: str = Field(..., description="Full address")
    road_address: str | None = Field(None, description="Road name address")
    coordinates: Coordinates
    place_name: str | None = Field(None, description="Place name if available")


class LocationResponse(BaseSchema):
    """Location search response."""

    results: list[LocationResult] = Field(default_factory=list)
    total: int = Field(0, description="Total number of results")
