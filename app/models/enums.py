"""공공데이터 관련 Enum 정의."""

from enum import Enum


class PropertyType(Enum):
    """부동산 유형."""

    LAND = "land"  # 토지
    COMMERCIAL = "commercial"  # 상업업무용
    DETACHED_HOUSE = "detached_house"  # 단독다가구
    ROW_HOUSE = "row_house"  # 연립다세대
    APARTMENT = "apartment"  # 아파트
    OFFICETEL = "officetel"  # 오피스텔


class TransactionType(Enum):
    """거래 유형."""

    SALE = "sale"  # 매매
    JEONSE = "jeonse"  # 전세
    MONTHLY_RENT = "monthly_rent"  # 월세


class PublicDataType(Enum):
    """공공데이터 유형 (수집 이력 추적용)."""

    CONTINUOUS_CADASTRAL = "continuous_cadastral"
    ANCILLARY_LAND = "ancillary_land"
    LAND_CHARACTERISTIC = "land_characteristic"
    LAND_USE_PLAN = "land_use_plan"
    LAND_AND_FOREST_INFO = "land_and_forest_info"
    OFFICIAL_LAND_PRICE = "official_land_price"
    REAL_ESTATE_TRANSACTION = "real_estate_transaction"
    BUILDING_REGISTER_HEADER = "building_register_header"
    BUILDING_REGISTER_FLOOR_DETAIL = "building_register_floor_detail"
    ADMINISTRATIVE_DIVISION = "administrative_division"
    ADMINISTRATIVE_EMD = "administrative_emd"
    ROAD_CENTER_LINE = "road_center_line"
    USE_REGION_DISTRICT = "use_region_district"
    GIS_BUILDING_INTEGRATED = "gis_building_integrated"
    STANDARD_LAND_PRICE = "standard_land_price"
    INDIVIDUAL_HOUSE_PRICE = "individual_house_price"
    APARTMENT_PRICE = "apartment_price"


class CollectionStatus(Enum):
    """데이터 수집 상태."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
