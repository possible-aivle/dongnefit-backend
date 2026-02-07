"""Map service for location-based operations."""

from abc import ABC, abstractmethod

import httpx

from app.config import settings
from app.schemas.map import Coordinates, LocationResponse, LocationResult


class MapProvider(ABC):
    """Abstract base class for map providers."""

    @abstractmethod
    async def search(self, query: str) -> LocationResponse:
        """Search for locations."""
        pass

    @abstractmethod
    async def geocode(self, address: str) -> dict:
        """Convert address to coordinates."""
        pass

    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> dict:
        """Convert coordinates to address."""
        pass


class NaverMapProvider(MapProvider):
    """Naver Map API provider."""

    BASE_URL = "https://dapi.naver.com/v2/local"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"NaverAK {api_key}"}

    async def search(self, query: str) -> LocationResponse:
        """Search for locations using Naver API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search/keyword.json",
                headers=self.headers,
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("documents", []):
                results.append(
                    LocationResult(
                        address=doc.get("address_name", ""),
                        road_address=doc.get("road_address_name"),
                        coordinates=Coordinates(
                            lat=float(doc.get("y", 0)),
                            lng=float(doc.get("x", 0)),
                        ),
                        place_name=doc.get("place_name"),
                    )
                )

            return LocationResponse(
                results=results,
                total=data.get("meta", {}).get("total_count", 0),
            )

    async def geocode(self, address: str) -> dict:
        """Convert address to coordinates using Naver API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search/address.json",
                headers=self.headers,
                params={"query": address},
            )
            response.raise_for_status()
            data = response.json()

            if documents := data.get("documents"):
                doc = documents[0]
                return {
                    "address": doc.get("address_name"),
                    "lat": float(doc.get("y", 0)),
                    "lng": float(doc.get("x", 0)),
                }
            return {"error": "Address not found"}

    async def reverse_geocode(self, lat: float, lng: float) -> dict:
        """Convert coordinates to address using Naver API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/geo/coord2address.json",
                headers=self.headers,
                params={"x": lng, "y": lat},
            )
            response.raise_for_status()
            data = response.json()

            if documents := data.get("documents"):
                doc = documents[0]
                address = doc.get("address", {})
                road_address = doc.get("road_address")
                return {
                    "address": address.get("address_name"),
                    "road_address": road_address.get("address_name") if road_address else None,
                    "lat": lat,
                    "lng": lng,
                }
            return {"error": "Location not found"}


class NaverCloudMapProvider(MapProvider):
    """Naver Cloud Platform Map API provider."""

    BASE_URL = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2"

    def __init__(self, client_id: str, client_secret: str):
        self.headers = {
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
        }

    async def search(self, query: str) -> LocationResponse:
        """Search for locations using Naver Cloud API."""
        # Implementation for Naver search
        return LocationResponse(results=[], total=0)

    async def geocode(self, address: str) -> dict:
        """Convert address to coordinates using Naver Cloud API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/geocoding",
                headers=self.headers,
                params={"query": address},
            )
            response.raise_for_status()
            data = response.json()

            if addresses := data.get("addresses"):
                addr = addresses[0]
                return {
                    "address": addr.get("roadAddress") or addr.get("jibunAddress"),
                    "lat": float(addr.get("y", 0)),
                    "lng": float(addr.get("x", 0)),
                }
            return {"error": "Address not found"}

    async def reverse_geocode(self, lat: float, lng: float) -> dict:
        """Convert coordinates to address using Naver Cloud API."""
        return {"error": "Not implemented"}


class MapService:
    """Map service facade for location operations."""

    def __init__(self):
        self.provider = self._get_provider()

    def _get_provider(self) -> MapProvider:
        """Get the configured map provider."""
        if settings.map_provider == "naver_cloud":
            # Naver Cloud Platform requires both client_id and client_secret
            return NaverCloudMapProvider(settings.map_api_key, "")
        else:
            # Default to Naver
            return NaverMapProvider(settings.map_api_key)

    async def search(self, query: str) -> LocationResponse:
        """Search for locations."""
        return await self.provider.search(query)

    async def geocode(self, address: str) -> dict:
        """Convert address to coordinates."""
        return await self.provider.geocode(address)

    async def reverse_geocode(self, lat: float, lng: float) -> dict:
        """Convert coordinates to address."""
        return await self.provider.reverse_geocode(lat, lng)
