"""Agent-facing helpers for convenience (생활편의시설) data."""

from __future__ import annotations

from typing import Any

from app.core.public_data.convenience import ConvenienceRepository


class ConvenienceToolService:
    """Wrapper around ConvenienceRepository for name search and proximity search."""

    def __init__(self, repo: ConvenienceRepository | None = None):
        self.repo = repo or ConvenienceRepository()

    def search(self, query: str, category: str | None = None, region: str | None = None, limit: int = 20) -> dict[str, Any]:
        grouped = self.repo.search(query, category=category, region=region, limit_per_group=limit)
        total = sum(len(v) for v in grouped.values())
        return {
            "query": query,
            "count": total,
            "facilities": grouped,
        }

    def near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        grouped = self.repo.search_near(lat, lng, radius_km=radius_km, category=category, limit_per_group=limit)
        total = sum(len(v) for v in grouped.values())
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": total,
            "distance_note": "직선거리 기반(도보시간 추정치)",
            "facilities": grouped,
        }
