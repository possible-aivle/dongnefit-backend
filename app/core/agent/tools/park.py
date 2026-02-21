"""Agent-facing helpers for park data (도시공원)."""

from __future__ import annotations

from typing import Any

from app.core.public_data.park import ParkRepository


class ParkToolService:
    """Thin wrapper around `ParkRepository` for agent/services usage."""

    def __init__(self, repo: ParkRepository | None = None):
        self.repo = repo or ParkRepository()

    def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        parks = self.repo.search(query, region=region, limit=limit)
        return {
            "query": query,
            "region": region,
            "count": len(parks),
            "parks": parks,
        }

    def near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        limit: int = 20,
    ) -> dict[str, Any]:
        results = self.repo.search_near(lat, lng, radius_km=radius_km, limit=limit)
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(results),
            "distance_note": "직선거리 기반(도보시간 추정치)",
            "parks": results,
        }
