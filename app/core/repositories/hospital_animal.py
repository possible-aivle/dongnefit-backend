"""Animal hospital (동물 관련 시설) data repository backed by local CSV files."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import Transformer

_DATA_DIR = Path(__file__).parent.parent / "api_data" / "hospital_animal"

_EPSG5174_TO_WGS84 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

_FILES: dict[str, str] = {
    "동물병원": "동물_동물병원_전처리.csv",
    "동물약국": "동물_동물약국_전처리.csv",
    "동물미용업": "동물_동물미용업_전처리.csv",
}


def _to_float(value: Any) -> float | None:
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _walk_minutes_est(distance_m: float) -> int:
    return max(1, round(distance_m / 80.0))


def _vectorized_transform(
    df: pd.DataFrame, x_col: str, y_col: str
) -> tuple[np.ndarray, np.ndarray]:
    """EPSG:5174 → WGS84 벡터 변환."""
    x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(dtype=np.float64)
    y = pd.to_numeric(df[y_col], errors="coerce").to_numpy(dtype=np.float64)
    valid = np.isfinite(x) & np.isfinite(y) & (x != 0) & (y != 0)
    lngs = np.full(len(x), np.nan)
    lats = np.full(len(x), np.nan)
    if valid.any():
        lng_arr, lat_arr = _EPSG5174_TO_WGS84.transform(x[valid], y[valid])
        lngs[valid] = lng_arr
        lats[valid] = lat_arr
    return lats, lngs


class AnimalHospitalRepository:
    """Lazy-loading repository for 동물 관련 시설 data."""

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _DATA_DIR
        self._df: pd.DataFrame | None = None

    def _load_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        frames: list[pd.DataFrame] = []
        for category, filename in _FILES.items():
            path = self._data_dir / filename
            if not path.exists():
                continue
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="cp949")
            df["_category"] = category
            frames.append(df)
        if not frames:
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {self._data_dir}")
        combined = pd.concat(frames, ignore_index=True)
        lats, lngs = _vectorized_transform(combined, "좌표정보(X)", "좌표정보(Y)")
        combined["_lat"] = lats
        combined["_lng"] = lngs
        self._df = combined
        return self._df

    def search(
        self,
        query: str,
        category: str | None = None,
        region: str | None = None,
        limit_per_group: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        """사업장명/주소 키워드로 동물 관련 시설을 검색합니다. 업태구분명별 그룹핑 결과 반환. 각 그룹별로 limit_per_group개까지만 반환합니다."""
        df = self._load_df()
        q = str(query or "").strip().lower()
        if not q:
            return {}
        mask = (
            df["사업장명"].astype(str).str.lower().str.contains(q, na=False)
            | df["도로명주소"].astype(str).str.lower().str.contains(q, na=False)
            | df["지번주소"].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered = df[mask]
        if category:
            filtered = filtered[filtered["_category"] == category]
        if region:
            r = region.strip().lower()
            mask_r = filtered["도로명주소"].astype(str).str.lower().str.contains(
                r, na=False
            ) | filtered["지번주소"].astype(str).str.lower().str.contains(r, na=False)
            filtered = filtered[mask_r]
        return _group_by_biz_type(list(filtered.iterrows()), limit_per_group=limit_per_group)

    def search_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        category: str | None = None,
        limit_per_group: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        """좌표(위도/경도) 기준 반경 내 동물 관련 시설을 업태구분명별 그룹핑하여 거리순으로 반환합니다. 각 그룹별로 limit_per_group개까지만 반환합니다."""
        df = self._load_df()
        df_valid = df.dropna(subset=["_lat", "_lng"])
        if category:
            df_valid = df_valid[df_valid["_category"] == category]

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
            return {}

        dlat = np.radians(candidates["_lat"].to_numpy() - lat)
        dlng = np.radians(candidates["_lng"].to_numpy() - lng)
        a = (
            np.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat))
            * np.cos(np.radians(candidates["_lat"].to_numpy()))
            * np.sin(dlng / 2) ** 2
        )
        candidates["_dist_km"] = 2 * 6371.0 * np.arcsin(np.sqrt(a))
        nearby = candidates[candidates["_dist_km"] <= radius_km].sort_values("_dist_km")

        groups: dict[str, list[dict[str, Any]]] = {}
        for _, row in nearby.iterrows():
            key = _get_group_key(row)
            if key in groups and len(groups[key]) >= limit_per_group:
                continue
            d_m = round(float(row["_dist_km"]) * 1000)
            entry = _row_to_dict(row)
            entry["distance_m"] = d_m
            entry["walk_time_min_est"] = _walk_minutes_est(d_m)
            groups.setdefault(key, []).append(entry)
        return groups


def _clean_phone(value: Any) -> str | None:
    """전화번호를 문자열로 정리. float(예: 21234567.0) → '21234567'."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "name": str(row.get("사업장명") or ""),
        "category": str(row.get("_category") or ""),
        "address_road": str(row.get("도로명주소") or "") or None,
        "address_lot": str(row.get("지번주소") or "") or None,
        "lat": _to_float(row.get("_lat")),
        "lng": _to_float(row.get("_lng")),
        "phone": _clean_phone(row.get("전화번호")),
    }


def _get_group_key(row: Any) -> str:
    """업태구분명 우선, 없으면 _category(파일 기반 분류) 사용."""
    biz_type = row.get("업태구분명")
    if pd.notna(biz_type) and str(biz_type).strip():
        return str(biz_type)
    return str(row.get("_category") or "기타")


def _group_by_biz_type(
    rows: list[tuple], limit_per_group: int = 20
) -> dict[str, list[dict[str, Any]]]:
    """Row 목록을 업태구분명 기준으로 그룹핑합니다. 각 그룹별로 limit_per_group개까지만 반환합니다."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for _, row in rows:
        key = _get_group_key(row)
        if key not in groups:
            groups[key] = []
        if len(groups[key]) < limit_per_group:
            groups[key].append(_row_to_dict(row))
    return groups
