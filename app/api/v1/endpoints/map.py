"""Map service endpoints."""

from fastapi import APIRouter

from app.schemas.map import LocationResponse, LocationSearch
from app.services.map.service import MapService

router = APIRouter()


@router.post("/search", response_model=LocationResponse)
async def search_location(request: LocationSearch) -> LocationResponse:
    """Search for location by address or keyword."""
    service = MapService()
    return await service.search(request.query)


@router.get("/geocode")
async def geocode(address: str) -> dict:
    """Convert address to coordinates."""
    service = MapService()
    return await service.geocode(address)


@router.get("/reverse-geocode")
async def reverse_geocode(lat: float, lng: float) -> dict:
    """Convert coordinates to address."""
    service = MapService()
    return await service.reverse_geocode(lat, lng)
