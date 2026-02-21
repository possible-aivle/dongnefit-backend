"""Agent-facing helpers for store (대규모점포) data."""

from __future__ import annotations

from typing import Any

from app.core.public_data.store import StoreRepository


class StoreToolService:
    """Wrapper around StoreRepository for name search and proximity search."""

    def __init__(self, repo: StoreRepository | None = None):
        self.repo = repo or StoreRepository()

    def search(self, query: str, region: str | None = None, limit: int = 20) -> dict[str, Any]:
        stores = self.repo.search(query, region=region, limit=limit)
        return {
            "query": query,
            "count": len(stores),
            "stores": stores,
        }

    def near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        limit: int = 20,
    ) -> dict[str, Any]:
        stores = self.repo.search_near(lat, lng, radius_km=radius_km, limit=limit)
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(stores),
            "stores": stores,
        }
