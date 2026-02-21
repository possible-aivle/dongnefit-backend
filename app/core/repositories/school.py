"""School data repository backed by local JSON files (학교 위치/학구)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def _get_school_data_dir() -> Path:
    """Return default school data directory: app/core/api_data/school/"""
    this_file = Path(__file__)
    # app/repositories/school.py -> app/core/api_data/school/
    return this_file.parent.parent / "api_data" / "school"


@dataclass(frozen=True)
class SchoolInfo:
    school_id: str
    school_name: str
    address: str
    latitude: float
    longitude: float
    school_type: str  # '초등학교', '중학교', '고등학교'


def _load_records_from_json(path: Path) -> list[dict[str, Any]]:
    """Load records from a public-data JSON file with {'fields': [...], 'records': [...]} structure."""
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


def _walk_minutes_est(distance_m: float) -> int:
    """Estimate walking minutes from distance in meters (~80m/min)."""
    return max(1, round(distance_m / 80.0))


class SchoolRepository:
    """Lazy-loading repository for school location and zone data."""

    _LOCATION_FILE = "전국초중등학교위치표준데이터.json"
    _ELEM_ZONE_FILE = "전국초등학교통학구역표준데이터.json"
    _MIDDLE_ZONE_FILE = "전국중학교학교군표준데이터.json"
    _HIGH_ZONE_FILE = "전국고등학교학교군표준데이터.json"
    _HIGH_UNEQUAL_FILE = "전국고등학교비평준화지역표준데이터.json"
    _EDU_ADMIN_FILE = "전국교육행정구역표준데이터.json"
    _ZONE_LINK_FILE = "전국학교학구도연계정보표준데이터.json"

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _get_school_data_dir()
        self._df_location: pd.DataFrame | None = None
        self._zone_cache: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------

    def _load_location_df(self) -> pd.DataFrame:
        if self._df_location is not None:
            return self._df_location
        records = _load_records_from_json(self._data_dir / self._LOCATION_FILE)
        self._df_location = pd.DataFrame(records)
        return self._df_location

    def _load_zone_records(self, filename: str) -> list[dict[str, Any]]:
        if filename not in self._zone_cache:
            self._zone_cache[filename] = _load_records_from_json(self._data_dir / filename)
        return self._zone_cache[filename]

    def _get_zone_filename(self, level: str) -> str:
        lv = str(level or "").strip().lower()
        mapping = {
            "elem": self._ELEM_ZONE_FILE,
            "elementary": self._ELEM_ZONE_FILE,
            "초": self._ELEM_ZONE_FILE,
            "초등": self._ELEM_ZONE_FILE,
            "초등학교": self._ELEM_ZONE_FILE,
            "middle": self._MIDDLE_ZONE_FILE,
            "mid": self._MIDDLE_ZONE_FILE,
            "중": self._MIDDLE_ZONE_FILE,
            "중등": self._MIDDLE_ZONE_FILE,
            "중학교": self._MIDDLE_ZONE_FILE,
            "high": self._HIGH_ZONE_FILE,
            "고": self._HIGH_ZONE_FILE,
            "고등": self._HIGH_ZONE_FILE,
            "고등학교": self._HIGH_ZONE_FILE,
            "high_unequal": self._HIGH_UNEQUAL_FILE,
            "unequal": self._HIGH_UNEQUAL_FILE,
            "비평준화": self._HIGH_UNEQUAL_FILE,
            "edu_admin": self._EDU_ADMIN_FILE,
            "education_admin": self._EDU_ADMIN_FILE,
            "행정": self._EDU_ADMIN_FILE,
            "교육행정": self._EDU_ADMIN_FILE,
        }
        if lv not in mapping:
            raise ValueError(
                f"level must be one of: elem, middle, high, high_unequal, edu_admin (got: {level!r})"
            )
        return mapping[lv]

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def search_by_region(
        self,
        region_keyword: str,
        school_type: str | None = None,
        limit: int = 20,
    ) -> list[SchoolInfo]:
        """Search schools where address contains all keywords in region_keyword."""
        df = self._load_location_df()
        keywords = [k for k in str(region_keyword or "").split() if k]
        if not keywords:
            return []

        condition: pd.Series | None = None
        for kw in keywords:
            term = df["소재지도로명주소"].str.contains(kw, na=False) | df[
                "소재지지번주소"
            ].str.contains(kw, na=False)
            condition = term if condition is None else (condition & term)

        sub = df[condition]
        if school_type:
            sub = sub[sub["학교급구분"].str.contains(school_type, na=False)]

        results: list[SchoolInfo] = []
        for _, row in sub.head(limit).iterrows():
            results.append(
                SchoolInfo(
                    school_id=str(row.get("학교ID", "") or ""),
                    school_name=str(row.get("학교명", "") or ""),
                    address=str(row.get("소재지도로명주소") or row.get("소재지지번주소") or ""),
                    latitude=float(row.get("위도") or 0.0),
                    longitude=float(row.get("경도") or 0.0),
                    school_type=str(row.get("학교급구분", "") or ""),
                )
            )
        return results

    def search_by_name(
        self,
        school_name: str,
        region_keyword: str | None = None,
        limit: int = 10,
    ) -> list[SchoolInfo]:
        """Search schools by name substring, optionally filtered by region."""
        df = self._load_location_df()
        sub = df[df["학교명"].str.contains(str(school_name or ""), na=False)]
        if region_keyword:
            for kw in str(region_keyword).split():
                sub = sub[
                    sub["소재지도로명주소"].str.contains(kw, na=False)
                    | sub["소재지지번주소"].str.contains(kw, na=False)
                ]

        results: list[SchoolInfo] = []
        for _, row in sub.head(limit).iterrows():
            results.append(
                SchoolInfo(
                    school_id=str(row.get("학교ID", "") or ""),
                    school_name=str(row.get("학교명", "") or ""),
                    address=str(row.get("소재지도로명주소") or row.get("소재지지번주소") or ""),
                    latitude=float(row.get("위도") or 0.0),
                    longitude=float(row.get("경도") or 0.0),
                    school_type=str(row.get("학교급구분", "") or ""),
                )
            )
        return results

    def search_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 1.0,
        school_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find schools within radius_km of a WGS84 point."""
        df = self._load_location_df().copy()
        df["_lat"] = pd.to_numeric(df.get("위도", pd.Series(dtype=float)), errors="coerce")
        df["_lng"] = pd.to_numeric(df.get("경도", pd.Series(dtype=float)), errors="coerce")
        df = df.dropna(subset=["_lat", "_lng"])

        if school_type:
            df = df[df["학교급구분"].str.contains(school_type, na=False)]

        # Bounding box pre-filter for performance
        rkm = max(0.01, float(radius_km))
        dlat = rkm / 111.0
        dlng = rkm / max(1e-6, 111.0 * abs(math.cos(math.radians(lat))))
        df = df[
            (df["_lat"] >= lat - dlat)
            & (df["_lat"] <= lat + dlat)
            & (df["_lng"] >= lng - dlng)
            & (df["_lng"] <= lng + dlng)
        ]

        rows: list[tuple[float, dict[str, Any]]] = []
        r_m = rkm * 1000.0
        for _, row in df.iterrows():
            rlat, rlng = float(row["_lat"]), float(row["_lng"])
            # Haversine distance
            phi1, phi2 = math.radians(lat), math.radians(rlat)
            dphi = math.radians(rlat - lat)
            dlambda_ = math.radians(rlng - lng)
            a = (
                math.sin(dphi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda_ / 2) ** 2
            )
            d_m = 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            if d_m <= r_m:
                rows.append(
                    (
                        d_m,
                        {
                            "school_id": str(row.get("학교ID", "") or ""),
                            "name": str(row.get("학교명", "") or ""),
                            "type": str(row.get("학교급구분", "") or ""),
                            "address": str(
                                row.get("소재지도로명주소") or row.get("소재지지번주소") or ""
                            ),
                            "lat": rlat,
                            "lng": rlng,
                            "distance_m": int(round(d_m)),
                            "walk_time_min_est": _walk_minutes_est(d_m),
                            "distance_note": "직선거리 기반(도보시간 추정치)",
                        },
                    )
                )

        rows.sort(key=lambda x: x[0])
        return [item for _, item in rows[:limit]]

    def search_zones(
        self,
        level: str,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search school zone/admin datasets by substring. No lat/lng in these datasets."""
        filename = self._get_zone_filename(level)
        records = self._load_zone_records(filename)
        q = str(query or "").strip().lower()
        if not q:
            return []

        results: list[dict[str, Any]] = []
        for r in records:
            hay = " ".join(str(v) for v in r.values() if v is not None).lower()
            if q in hay:
                results.append(r)
                if len(results) >= limit:
                    break
        return results

    def zone_by_school(
        self,
        school_name: str,
        school_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find zone info for a school via 학교학구도연계정보 link table."""
        links = self._load_zone_records(self._ZONE_LINK_FILE)
        elem = {r.get("학구ID"): r for r in self._load_zone_records(self._ELEM_ZONE_FILE)}
        mid = {r.get("학구ID"): r for r in self._load_zone_records(self._MIDDLE_ZONE_FILE)}
        high = {r.get("학구ID"): r for r in self._load_zone_records(self._HIGH_ZONE_FILE)}

        q = str(school_name or "").strip().lower()
        st = str(school_type or "").strip().lower()

        results: list[dict[str, Any]] = []
        for m in links:
            name = str(m.get("학교명") or "").lower()
            t = str(m.get("학교급구분") or "")
            if q not in name:
                continue
            if st and st not in t.lower():
                continue
            zid = m.get("학구ID")
            results.append(
                {
                    "school_id": m.get("학교ID"),
                    "school_name": m.get("학교명"),
                    "school_type": m.get("학교급구분"),
                    "zone_id": zid,
                    "elem_zone": elem.get(zid),
                    "middle_zone": mid.get(zid),
                    "high_zone": high.get(zid),
                }
            )
            if len(results) >= limit:
                break
        return results
