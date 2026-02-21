"""Convenience (생활편의시설) data repository backed by local CSV files."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pyproj import Transformer

_DATA_DIR = Path(__file__).parent.parent / "api_data" / "convenience"

_EPSG5174_TO_WGS84 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

# EPSG:5174 좌표 사용 파일들
_FILES_EPSG: dict[str, str] = {
    "대규모점포": "생활_대규모점포_전처리.csv",
    "골프장": "생활_골프장_전처리.csv",
    "목욕장업": "생활_목욕장업_전처리.csv",
    "미용업": "생활_미용업_전처리.csv",
    "세탁업": "생활_세탁업_전처리.csv",
    "수영장업": "생활_수영장업_전처리.csv",
    "이용업": "생활_이용업_전처리.csv",
    "체력단련장업": "생활_체력단련장업_전처리.csv",
}

# WGS84 좌표 사용 파일 (세차장)
_FILE_WGS84: dict[str, str] = {
    "세차장": "세차장정보_전처리.csv",
}


def _to_float(value: Any) -> float | None:
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


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


class ConvenienceRepository:
    """Lazy-loading repository for 생활편의시설 data."""

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _DATA_DIR
        self._df: pd.DataFrame | None = None

    def _load_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        frames: list[pd.DataFrame] = []

        # EPSG:5174 파일 로드
        for category, filename in _FILES_EPSG.items():
            path = self._data_dir / filename
            if not path.exists():
                continue
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="cp949")
            df["_category"] = category
            # 주소 컬럼 통일
            if "도로명전체주소" in df.columns and "도로명주소" not in df.columns:
                df["도로명주소"] = df["도로명전체주소"]
            if "소재지전체주소" in df.columns and "지번주소" not in df.columns:
                df["지번주소"] = df["소재지전체주소"]
            lats, lngs = _vectorized_transform(df, "좌표정보(X)", "좌표정보(Y)")
            df["_lat"] = lats
            df["_lng"] = lngs
            frames.append(df)

        # WGS84 파일 (세차장) 로드
        for category, filename in _FILE_WGS84.items():
            path = self._data_dir / filename
            if not path.exists():
                continue
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="cp949")
            df["_category"] = category
            # 세차장은 주소 컬럼명이 다름
            if "소재지도로명주소" in df.columns:
                df["도로명주소"] = df["소재지도로명주소"]
            if "소재지지번주소" in df.columns:
                df["지번주소"] = df["소재지지번주소"]
            if "세차장전화번호" in df.columns:
                df["전화번호"] = df["세차장전화번호"]
            df["_lat"] = pd.to_numeric(df.get("WGS84위도"), errors="coerce")
            df["_lng"] = pd.to_numeric(df.get("WGS84경도"), errors="coerce")
            frames.append(df)

        if not frames:
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {self._data_dir}")
        combined = pd.concat(frames, ignore_index=True)
        self._df = combined
        return self._df

    def search(
        self,
        query: str,
        category: str | None = None,
        region: str | None = None,
        limit_per_group: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        """사업장명/주소 키워드로 생활편의시설을 검색합니다. 업태구분명별 그룹핑 결과 반환. 각 그룹별로 limit_per_group개까지만 반환합니다."""
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
        return _group_by_category(list(filtered.iterrows()), limit_per_group=limit_per_group)

    def search_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        category: str | None = None,
        limit_per_group: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        """좌표(위도/경도) 기준 반경 내 생활편의시설을 업태구분명별 그룹핑하여 거리순으로 반환합니다. 각 그룹별로 limit_per_group개까지만 반환합니다."""
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


def _row_to_dict(row: Any) -> dict[str, Any]:
    # category: 업태구분명 우선, 없으면 _category(파일 기반 분류) 사용
    biz_type = row.get("업태구분명")
    if pd.notna(biz_type) and str(biz_type).strip():
        category = str(biz_type)
    else:
        category = str(row.get("_category") or "")

    return {
        "name": str(row.get("사업장명") or ""),
        "category": category,
        "address_road": str(row.get("도로명주소") or "") or None,
        "address_lot": str(row.get("지번주소") or "") or None,
        "lat": _to_float(row.get("_lat")),
        "lng": _to_float(row.get("_lng")),
        "phone": _clean_phone(row.get("전화번호")),
    }


def _get_group_key(row: Any) -> str:
    """_category(파일 기반 분류)로 그룹핑."""
    return str(row.get("_category") or "기타")


def _group_by_category(
    rows: list[tuple], limit_per_group: int = 20
) -> dict[str, list[dict[str, Any]]]:
    """Row 목록을 _category 기준으로 그룹핑합니다. 각 그룹별로 limit_per_group개까지만 반환합니다."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for _, row in rows:
        key = _get_group_key(row)
        if key not in groups:
            groups[key] = []
        if len(groups[key]) < limit_per_group:
            groups[key].append(_row_to_dict(row))
    return groups
