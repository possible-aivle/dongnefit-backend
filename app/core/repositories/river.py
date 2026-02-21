"""River data repository backed by local JSON file (전국하천표준데이터).

search()      — 하천명 키워드로 로컬 데이터 검색
search_near() — VWorld 하천망 API 사용 (tools/river.py 참조)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


def _get_river_data_dir() -> Path:
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


# ---------------------------------------------------------------------------
# Geometry helpers for VWorld API LineString results
# ---------------------------------------------------------------------------


def _point_to_segment_km(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    """평면 근사로 점 P에서 선분 AB까지의 최단 거리(km)를 반환합니다.
    좌표계: x=경도, y=위도 (EPSG:4326).
    """
    scale_x = 111.0 * math.cos(math.radians(py))
    scale_y = 111.0

    px_km, py_km = px * scale_x, py * scale_y
    ax_km, ay_km = ax * scale_x, ay * scale_y
    bx_km, by_km = bx * scale_x, by * scale_y

    abx, aby = bx_km - ax_km, by_km - ay_km
    apx, apy = px_km - ax_km, py_km - ay_km

    ab2 = abx**2 + aby**2
    if ab2 == 0.0:
        return math.sqrt(apx**2 + apy**2)

    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab2))
    cx_km = ax_km + t * abx
    cy_km = ay_km + t * aby
    return math.sqrt((px_km - cx_km) ** 2 + (py_km - cy_km) ** 2)


def min_dist_to_linestring(lat: float, lng: float, coordinates: list[list[float]]) -> float:
    """점(lat, lng)에서 LineString까지의 최단 거리(km)를 반환합니다.
    coordinates: GeoJSON 형식 [[lng, lat], [lng, lat], ...]
    """
    if len(coordinates) < 2:
        return float("inf")
    min_d = float("inf")
    for i in range(len(coordinates) - 1):
        a_lng, a_lat = coordinates[i][0], coordinates[i][1]
        b_lng, b_lat = coordinates[i + 1][0], coordinates[i + 1][1]
        d = _point_to_segment_km(lng, lat, a_lng, a_lat, b_lng, b_lat)
        if d < min_d:
            min_d = d
    return min_d


def linestring_centroid(coordinates: list[list[float]]) -> tuple[float | None, float | None]:
    """LineString 좌표 목록의 중심점(lat, lng)을 반환합니다.
    coordinates: GeoJSON 형식 [[lng, lat], ...]
    """
    if not coordinates:
        return None, None
    lngs = [c[0] for c in coordinates if len(c) >= 2]
    lats = [c[1] for c in coordinates if len(c) >= 2]
    if not lats:
        return None, None
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def _extract_rings(geom_type: str, raw_coords: list) -> list[list[list[float]]]:
    """geometry에서 링(exterior ring) 목록을 추출합니다.
    반환값: [[lng, lat], ...] 형태의 링 목록.
    """
    if geom_type == "LineString":
        return [raw_coords]
    if geom_type == "MultiLineString":
        return raw_coords
    if geom_type == "Polygon":
        # raw_coords[0] = exterior ring
        return [raw_coords[0]] if raw_coords else []
    if geom_type == "MultiPolygon":
        # raw_coords = [polygon, ...], polygon = [exterior_ring, ...holes]
        return [poly[0] for poly in raw_coords if poly]
    return []


def feature_to_river_dict(feat: dict[str, Any], lat: float, lng: float) -> dict[str, Any] | None:
    """VWorld API Feature를 river dict로 변환합니다.
    LineString / MultiLineString / Polygon / MultiPolygon 모두 지원합니다.
    """
    geom = feat.get("geometry") or {}
    geom_type = geom.get("type", "")
    raw_coords = geom.get("coordinates", [])

    rings = _extract_rings(geom_type, raw_coords)
    if not rings:
        return None

    valid_rings = [r for r in rings if len(r) >= 2]
    if not valid_rings:
        return None

    # 모든 링에서 최단 거리
    dist_km = min(min_dist_to_linestring(lat, lng, ring) for ring in valid_rings)

    # 중심점: 모든 링의 좌표를 합쳐서 계산
    all_coords: list[list[float]] = [c for ring in valid_rings for c in ring]
    c_lat, c_lng = linestring_centroid(all_coords)

    props = feat.get("properties") or {}
    return {
        "name": str(props.get("riv_nm") or ""),
        "type": str(props.get("cat_nam") or ""),
        "lat": c_lat,
        "lng": c_lng,
        "distance_km": round(dist_km, 3),
    }


# ---------------------------------------------------------------------------
# Repository (name-based search using local JSON)
# ---------------------------------------------------------------------------


class RiverRepository:
    """Lazy-loading repository for national river (하천) data — name search only.
    Proximity search uses VWorld API (see tools/river.py).
    """

    _RIVER_FILE = "전국하천표준데이터.json"

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _get_river_data_dir()
        self._df: pd.DataFrame | None = None

    def _load_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        records = _load_records_from_json(self._data_dir / self._RIVER_FILE)
        df = pd.DataFrame(records)
        self._df = df
        return self._df

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """하천명(제1/2지류 포함)으로 하천을 검색합니다."""
        df = self._load_df()
        q = str(query or "").strip().lower()
        if not q:
            return []

        mask = (
            df["하천명"].str.lower().str.contains(q, na=False)
            | df["제1지류명"].str.lower().str.contains(q, na=False)
            | df["제2지류명"].str.lower().str.contains(q, na=False)
        )
        return [_row_to_dict(row) for _, row in df[mask].head(limit).iterrows()]


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "name": str(row.get("하천명") or ""),
        "type": str(row.get("하천구분명") or ""),
        "length_km": _to_float(row.get("하천길이")),
        "start_location": str(row.get("시점위치") or "") or None,
        "end_location": str(row.get("종점위치") or "") or None,
        "manager": str(row.get("관리기관명") or "") or None,
    }
