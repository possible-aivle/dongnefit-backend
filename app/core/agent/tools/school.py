"""Agent-facing helpers for school data (학교 위치/학구)."""

from __future__ import annotations

from typing import Any

from app.core.public_data.school import SchoolRepository


class SchoolToolService:
    """Thin wrapper around `SchoolRepository` for agent/services usage."""

    def __init__(self, repo: SchoolRepository | None = None):
        self.repo = repo or SchoolRepository()

    def search(
        self,
        region_keyword: str,
        school_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        schools = self.repo.search_by_region(region_keyword, school_type=school_type, limit=limit)
        return {
            "query": region_keyword,
            "school_type": school_type,
            "count": len(schools),
            "schools": [
                {
                    "name": s.school_name,
                    "type": s.school_type,
                    "address": s.address,
                    "lat": s.latitude,
                    "lng": s.longitude,
                }
                for s in schools
            ],
        }

    def get_latlng(
        self,
        school_name: str,
        region_keyword: str | None = None,
    ) -> dict[str, Any]:
        schools = self.repo.search_by_name(school_name, region_keyword=region_keyword)
        return {
            "query": {"school_name": school_name, "region_keyword": region_keyword},
            "count": len(schools),
            "results": [
                {
                    "name": s.school_name,
                    "address": s.address,
                    "lat": s.latitude,
                    "lng": s.longitude,
                    "type": s.school_type,
                }
                for s in schools
            ],
        }

    def get_address(
        self,
        school_name: str,
        region_keyword: str | None = None,
    ) -> dict[str, Any]:
        schools = self.repo.search_by_name(school_name, region_keyword=region_keyword)
        return {
            "query": {"school_name": school_name, "region_keyword": region_keyword},
            "count": len(schools),
            "results": [
                {"name": s.school_name, "address": s.address, "type": s.school_type}
                for s in schools
            ],
        }

    def near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 1.0,
        school_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        results = self.repo.search_near(lat, lng, radius_km=radius_km, school_type=school_type, limit=limit)
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "school_type": school_type,
            "count": len(results),
            "results": results,
        }

    def near_grouped(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        limit_per_type: int = 5,
    ) -> dict[str, Any]:
        """초등학교/중학교/고등학교를 각각 limit_per_type개씩 거리순으로 반환."""
        school_types = ["초등학교", "중학교", "고등학교"]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for school_type in school_types:
            raw = self.repo.search_near(
                lat, lng, radius_km=radius_km, school_type=school_type, limit=limit_per_type
            )
            grouped[school_type] = [
                {
                    "name": r["name"],
                    "type": r["type"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "distance_m": r["distance_m"],
                    "walk_time_min_est": r["walk_time_min_est"],
                }
                for r in raw
            ]
        return {
            "ok": True,
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "limit_per_type": limit_per_type,
            "distance_note": "직선거리 기반(도보시간 추정치)",
            "schools": grouped,
        }

    def zone_search(
        self,
        level: str,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        results = self.repo.search_zones(level, query, limit=limit)
        return {
            "ok": True,
            "level": level,
            "query": query,
            "count": len(results),
            "results": results,
            "note": "이 데이터셋에는 위도/경도 필드가 없습니다(학구ID/학교ID 등 식별자 중심).",
        }

    def zone_by_school(
        self,
        school_name: str,
        school_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        results = self.repo.zone_by_school(school_name, school_type=school_type, limit=limit)
        return {
            "ok": True,
            "school_name_query": school_name,
            "school_type_filter": school_type,
            "count": len(results),
            "results": results,
            "note": "학구/학교군 데이터에는 좌표가 없으므로, 좌표가 필요하면 학교위치 데이터와 별도로 결합해야 합니다.",
        }
