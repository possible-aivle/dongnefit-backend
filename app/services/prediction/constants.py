"""피쳐 정의 및 카테고리 매핑 상수."""

# 지목 원핫인코딩 카테고리 (주요 9개, 나머지는 '기타'로 매핑)
JIMOK_CATEGORIES: list[str] = [
    "대",      # 대지
    "전",      # 전
    "답",      # 답
    "임",      # 임야
    "잡",      # 잡종지
    "공",      # 공장용지
    "도",      # 도로
    "과",      # 과수원
    "목",      # 목장용지
]

# 용도지역 그룹핑 (4개 대분류)
USE_ZONE_GROUPS: dict[str, list[str]] = {
    "주거": [
        "제1종전용주거지역", "제2종전용주거지역",
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
        "준주거지역",
    ],
    "상업": [
        "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역",
    ],
    "공업": [
        "전용공업지역", "일반공업지역", "준공업지역",
    ],
    "녹지": [
        "보전녹지지역", "생산녹지지역", "자연녹지지역",
    ],
}

# 용도지역 → 그룹 역매핑 (런타임 생성)
USE_ZONE_TO_GROUP: dict[str, str] = {}
for group, zones in USE_ZONE_GROUPS.items():
    for zone in zones:
        USE_ZONE_TO_GROUP[zone] = group

# ── 시계열 모드 피쳐 (multi-year history 있을 때) ──
TIMESERIES_FEATURE_NAMES: list[str] = [
    # 토지 기본 (~16)
    "area_log",
    "jimok_대", "jimok_전", "jimok_답", "jimok_임", "jimok_잡",
    "jimok_공", "jimok_도", "jimok_과", "jimok_목",
    "use_zone_주거", "use_zone_상업", "use_zone_공업", "use_zone_녹지",
    "ownership_private",
    "owner_count",
    # 가격 시계열 (~10)
    "price_level_log",
    "price_lag_1", "price_lag_2", "price_lag_3",
    "rolling_mean_3", "rolling_mean_5",
    "rolling_std_3",
    "yoy_change",
    "trend_slope",
    "history_length",
    # 건물 정보 (6)
    "has_building",
    "floor_area_log",
    "bcr",
    "far",
    "above_ground_floors",
    "building_age",
    # 지역 통계 (3)
    "avg_sale_price_log",
    "sale_volume_log",
    "avg_deposit_log",
]

# ── 횡단면 모드 피쳐 (single-year data일 때) ──
# 가격 시계열 피쳐를 제외한 나머지 (가격은 타겟이므로 피쳐에서 제외)
CROSS_SECTIONAL_FEATURE_NAMES: list[str] = [
    # 토지 기본 (~16)
    "area_log",
    "jimok_대", "jimok_전", "jimok_답", "jimok_임", "jimok_잡",
    "jimok_공", "jimok_도", "jimok_과", "jimok_목",
    "use_zone_주거", "use_zone_상업", "use_zone_공업", "use_zone_녹지",
    "ownership_private",
    "owner_count",
    # 건물 정보 (6)
    "has_building",
    "floor_area_log",
    "bcr",
    "far",
    "above_ground_floors",
    "building_age",
    # 지역 통계 (3)
    "avg_sale_price_log",
    "sale_volume_log",
    "avg_deposit_log",
]

PREDICTION_YEARS: int = 5

# 기본 연간 공시지가 상승률 (데이터 부족 시 사용)
DEFAULT_ANNUAL_GROWTH_RATE: float = 0.03

# ── 강화 횡단면 모드 피쳐 (지역 가격 컨텍스트 포함) ──
ENHANCED_CROSS_SECTIONAL_FEATURE_NAMES: list[str] = [
    *CROSS_SECTIONAL_FEATURE_NAMES,
    "price_per_sqm_log",
    "price_rank_in_sgg",
    "price_to_sgg_ratio",
    "sgg_growth_rate",
]
