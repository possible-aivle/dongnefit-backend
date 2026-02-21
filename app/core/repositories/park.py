"""Park data repository backed by local JSON file (전국도시공원정보표준데이터)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


def _get_park_data_dir() -> Path:
    return Path(__file__).parent.parent / "api_data" / "etc"


def _load_records_from_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "records" in data:
        records = data["records"]
        if isinstance(records, list):
            return records
    raise ValueError(f"예상하지 못한 JSON 구조입니다: {path}")


def _to_float(value: Any) -> float | None:
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _walk_minutes_est(distance_m: float) -> int:
    return max(1, round(distance_m / 80.0))


class ParkRepository:
    """Lazy-loading repository for national park (도시공원) location data."""

    _PARK_FILE = "전국도시공원정보표준데이터.json"

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _get_park_data_dir()
        self._df: pd.DataFrame | None = None

    def _load_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        records = _load_records_from_json(self._data_dir / self._PARK_FILE)
        df = pd.DataFrame(records)
        df["_lat"] = df["위도"].apply(_to_float)
        df["_lng"] = df["경도"].apply(_to_float)
        self._df = df
        return self._df

    def search(
        self,
        query: str,
        region: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """키워드(공원명/주소)와 선택적 지역명으로 공원을 검색합니다."""
        df = self._load_df()
        q = str(query or "").strip().lower()
        if not q:
            return []

        mask_query = (
            df["공원명"].str.lower().str.contains(q, na=False)
            | df["소재지도로명주소"].str.lower().str.contains(q, na=False)
            | df["소재지지번주소"].str.lower().str.contains(q, na=False)
        )
        filtered = df[mask_query]

        if region:
            r = region.strip().lower()
            mask_region = filtered["소재지도로명주소"].str.lower().str.contains(
                r, na=False
            ) | filtered["소재지지번주소"].str.lower().str.contains(r, na=False)
            filtered = filtered[mask_region]

        return [_row_to_dict(row) for _, row in filtered.head(limit).iterrows()]

    def search_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 2.0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """좌표(위도/경도) 기준 반경 내 공원을 거리순으로 반환합니다."""
        df = self._load_df()
        df_valid = df.dropna(subset=["_lat", "_lng"])

        # Bounding box pre-filter
        deg_lat = radius_km / 111.0
        deg_lng = radius_km / (111.0 * math.cos(math.radians(lat)))
        mask = (
            (df_valid["_lat"] >= lat - deg_lat)
            & (df_valid["_lat"] <= lat + deg_lat)
            & (df_valid["_lng"] >= lng - deg_lng)
            & (df_valid["_lng"] <= lng + deg_lng)
        )
        candidates = df_valid[mask].copy()

        if candidates.empty:
            return []

        def _haversine(row: Any) -> float:
            r = 6371.0
            dlat = math.radians(row["_lat"] - lat)
            dlng = math.radians(row["_lng"] - lng)
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(math.radians(lat))
                * math.cos(math.radians(row["_lat"]))
                * math.sin(dlng / 2) ** 2
            )
            return 2 * r * math.asin(math.sqrt(a))

        candidates["_dist_km"] = candidates.apply(_haversine, axis=1)
        nearby = candidates[candidates["_dist_km"] <= radius_km].sort_values("_dist_km")

        results = []
        for _, row in nearby.head(limit).iterrows():
            d_km = float(row["_dist_km"])
            d_m = round(d_km * 1000)
            entry = _row_to_dict(row)
            entry["distance_m"] = d_m
            entry["walk_time_min_est"] = _walk_minutes_est(d_m)
            results.append(entry)
        return results


def _row_to_dict(row: Any) -> dict[str, Any]:
    area = _to_float(row.get("공원면적"))
    return {
        "name": str(row.get("공원명") or ""),
        "type": str(row.get("공원구분") or ""),
        "address_road": str(row.get("소재지도로명주소") or "") or None,
        "address_lot": str(row.get("소재지지번주소") or "") or None,
        "lat": _to_float(row.get("위도")),
        "lng": _to_float(row.get("경도")),
        "area_m2": area,
        "manager": str(row.get("관리기관명") or "") or None,
    }
