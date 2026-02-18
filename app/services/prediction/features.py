"""피쳐 엔지니어링 함수.

Lot, BuildingRegisterGeneral, 실거래가 통계를 입력받아
XGBoost 모델 학습/예측에 사용할 피쳐 벡터를 생성한다.

두 가지 모드:
- 시계열 모드 (multi-year): build_feature_vector() — 가격 이력 포함 35개
- 횡단면 모드 (single-year): build_cross_sectional_vector() — 가격 제외 25개
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.services.prediction.constants import (
    CROSS_SECTIONAL_FEATURE_NAMES,
    ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES,
    JIMOK_CATEGORIES,
    TIMESERIES_FEATURE_NAMES,
    USE_ZONE_TO_GROUP,
)


def _safe_log(value: float | None, default: float = 0.0) -> float:
    """안전한 log 변환 (None/0/음수 처리)."""
    if value is None or value <= 0:
        return default
    return math.log1p(value)


def build_land_features(
    area: float | None,
    jimok: str | None,
    use_zone: str | None,
    ownership: str | None,
    owner_count: int | None,
) -> list[float]:
    """토지 기본 피쳐 (16개).

    Returns:
        [area_log, jimok_대..목 (9), use_zone_주거..녹지 (4), ownership_private, owner_count]
    """
    features: list[float] = []

    # area_log
    features.append(_safe_log(area))

    # jimok 원핫 (9개)
    jimok_str = (jimok or "")[:1]  # 첫 글자만
    for cat in JIMOK_CATEGORIES:
        features.append(1.0 if jimok_str == cat else 0.0)

    # use_zone 그룹 원핫 (4개)
    zone_group = USE_ZONE_TO_GROUP.get(use_zone or "", "")
    for grp in ["주거", "상업", "공업", "녹지"]:
        features.append(1.0 if zone_group == grp else 0.0)

    # ownership (개인=1, else=0)
    features.append(1.0 if ownership == "개인" else 0.0)

    # owner_count
    features.append(float(owner_count or 1))

    return features


def build_price_series_features(
    prices: list[dict[str, Any]],
    base_year: int,
) -> list[float]:
    """가격 시계열 피쳐 (10개). 시계열 모드 전용.

    prices: [{"base_year": "2020", "price_per_sqm": 1234567}, ...]
    base_year: 기준 연도 (이 연도까지의 데이터만 사용)

    Returns:
        [price_level_log, lag1~3, rolling_mean_3/5, rolling_std_3,
         yoy_change, trend_slope, history_length]
    """
    sorted_prices = sorted(
        [
            p for p in prices
            if int(p.get("base_year", 0)) <= base_year
            and p.get("price_per_sqm") is not None
        ],
        key=lambda p: int(p["base_year"]),
    )

    if not sorted_prices:
        return [0.0] * 10

    values = [float(p["price_per_sqm"]) for p in sorted_prices]
    n = len(values)

    current = values[-1]
    price_level_log = _safe_log(current)

    lag1 = _safe_log(values[-2]) if n >= 2 else price_level_log
    lag2 = _safe_log(values[-3]) if n >= 3 else lag1
    lag3 = _safe_log(values[-4]) if n >= 4 else lag2

    rolling_mean_3 = _safe_log(sum(values[-3:]) / min(n, 3))
    rolling_mean_5 = _safe_log(sum(values[-5:]) / min(n, 5))

    recent_3 = values[-3:] if n >= 3 else values
    rolling_std_3 = float(np.std(recent_3)) if len(recent_3) > 1 else 0.0

    if n >= 2 and values[-2] > 0:
        yoy_change = (values[-1] - values[-2]) / values[-2]
    else:
        yoy_change = 0.0

    if n >= 2:
        x = np.arange(n, dtype=float)
        y = np.array(values, dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])
        mean_price = float(np.mean(y))
        trend_slope = slope / mean_price if mean_price > 0 else 0.0
    else:
        trend_slope = 0.0

    history_length = float(n)

    return [
        price_level_log,
        lag1, lag2, lag3,
        rolling_mean_3, rolling_mean_5,
        rolling_std_3,
        yoy_change,
        trend_slope,
        history_length,
    ]


def build_building_features(
    building: dict[str, Any] | None,
    base_year: int,
) -> list[float]:
    """건물 정보 피쳐 (6개).

    Returns:
        [has_building, floor_area_log, bcr, far, above_ground_floors, building_age]
    """
    if building is None:
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    has_building = 1.0
    floor_area_log = _safe_log(building.get("total_floor_area"))
    bcr = float(building.get("bcr") or 0.0)
    far = float(building.get("far") or 0.0)
    floors = float(building.get("above_ground_floors") or 0)

    approval = building.get("approval_date", "")
    if approval and len(str(approval)) >= 4:
        try:
            approval_year = int(str(approval)[:4])
            building_age = float(base_year - approval_year)
        except (ValueError, TypeError):
            building_age = 0.0
    else:
        building_age = 0.0

    return [has_building, floor_area_log, bcr, far, floors, building_age]


def build_regional_features(
    sgg_stats: dict[str, float] | None,
) -> list[float]:
    """지역 통계 피쳐 (3개).

    Returns:
        [avg_sale_price_log, sale_volume_log, avg_deposit_log]
    """
    if sgg_stats is None:
        return [0.0, 0.0, 0.0]

    return [
        _safe_log(sgg_stats.get("avg_sale_price")),
        _safe_log(sgg_stats.get("sale_volume")),
        _safe_log(sgg_stats.get("avg_deposit")),
    ]


def build_feature_vector(
    area: float | None,
    jimok: str | None,
    use_zone: str | None,
    ownership: str | None,
    owner_count: int | None,
    prices: list[dict[str, Any]],
    base_year: int,
    building: dict[str, Any] | None,
    sgg_stats: dict[str, Any] | None,
) -> list[float]:
    """시계열 모드 전체 피쳐 벡터 (~35개).

    가격 이력이 있는 multi-year 데이터용.
    """
    vector = (
        build_land_features(area, jimok, use_zone, ownership, owner_count)
        + build_price_series_features(prices, base_year)
        + build_building_features(building, base_year)
        + build_regional_features(sgg_stats)
    )

    assert len(vector) == len(TIMESERIES_FEATURE_NAMES), (
        f"Feature vector length mismatch: {len(vector)} != {len(TIMESERIES_FEATURE_NAMES)}"
    )

    return vector


def build_cross_sectional_vector(
    area: float | None,
    jimok: str | None,
    use_zone: str | None,
    ownership: str | None,
    owner_count: int | None,
    base_year: int,
    building: dict[str, Any] | None,
    sgg_stats: dict[str, Any] | None,
) -> list[float]:
    """횡단면 모드 피쳐 벡터 (25개).

    가격 시계열 피쳐를 제외한 토지+건물+지역 피쳐.
    가격은 예측 타겟이므로 피쳐에 포함하지 않음.
    """
    vector = (
        build_land_features(area, jimok, use_zone, ownership, owner_count)
        + build_building_features(building, base_year)
        + build_regional_features(sgg_stats)
    )

    assert len(vector) == len(CROSS_SECTIONAL_FEATURE_NAMES), (
        f"Cross-sectional vector length mismatch: "
        f"{len(vector)} != {len(CROSS_SECTIONAL_FEATURE_NAMES)}"
    )

    return vector


def build_district_price_features(
    current_price: float | None,
    sgg_price_stats: dict[str, float] | None,
    sgg_growth_rate: float,
) -> list[float]:
    """지역 가격 컨텍스트 피쳐 (4개).

    필지 가격을 지역 평균 대비 상대값으로 표현하여
    같은 지목/면적이라도 비싼/싼 동네를 구분할 수 있게 한다.

    Returns:
        [price_per_sqm_log, price_rank_in_sgg, price_to_sgg_ratio, sgg_growth_rate]
    """
    price = float(current_price or 0)
    price_log = _safe_log(price)

    if sgg_price_stats and sgg_price_stats.get("mean_price", 0) > 0:
        mean_price = sgg_price_stats["mean_price"]
        median_price = sgg_price_stats.get("median_price", mean_price)

        # 지역 내 상대 순위: 중위값 대비 위치 (0~2 범위, 1이 중간)
        price_rank = price / median_price if median_price > 0 else 1.0
        price_rank = min(price_rank, 5.0)  # 극단값 클리핑

        # 지역 평균 대비 비율
        price_ratio = price / mean_price if mean_price > 0 else 1.0
        price_ratio = min(price_ratio, 5.0)
    else:
        price_rank = 1.0
        price_ratio = 1.0

    return [price_log, price_rank, price_ratio, sgg_growth_rate]


def build_enhanced_cross_sectional_vector(
    area: float | None,
    jimok: str | None,
    use_zone: str | None,
    ownership: str | None,
    owner_count: int | None,
    base_year: int,
    building: dict[str, Any] | None,
    sgg_stats: dict[str, Any] | None,
    current_price: float | None,
    sgg_price_stats: dict[str, float] | None,
    sgg_growth_rate: float,
) -> list[float]:
    """강화 횡단면 모드 피쳐 벡터 (29개).

    기존 25개 + 지역 가격 컨텍스트 4개.
    """
    vector = (
        build_land_features(area, jimok, use_zone, ownership, owner_count)
        + build_building_features(building, base_year)
        + build_regional_features(sgg_stats)
        + build_district_price_features(current_price, sgg_price_stats, sgg_growth_rate)
    )

    assert len(vector) == len(ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES), (
        f"Enhanced cross-sectional vector length mismatch: "
        f"{len(vector)} != {len(ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES)}"
    )

    return vector
