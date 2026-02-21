"""Agent-facing helpers for river data (하천)."""

from __future__ import annotations

from typing import Any

from app.core.public_data.river import RiverRepository, feature_to_river_dict
from app.core.public_data.vworld import VWorldClient


class RiverToolService:
    """Wrapper around RiverRepository (name search) and VWorld API (proximity search)."""

    def __init__(self, repo: RiverRepository | None = None):
        self.repo = repo or RiverRepository()

    def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        rivers = self.repo.search(query, limit=limit)
        return {
            "query": query,
            "count": len(rivers),
            "rivers": rivers,
        }

    async def near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """VWorld 하천망 API로 반경 내 하천을 실제 경로 기준 거리순으로 반환합니다."""
        client = VWorldClient()
        features = await client.get_rivers_near(lat, lng, radius_km=radius_km)

        results: list[dict[str, Any]] = []
        for feat in features:
            d = feature_to_river_dict(feat, lat, lng)
            if d is not None and d["distance_km"] <= radius_km:
                results.append(d)

        results.sort(key=lambda x: x["distance_km"])
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(results[:limit]),
            "rivers": results[:limit],
        }
