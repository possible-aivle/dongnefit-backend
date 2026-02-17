"""공공데이터 API 응답 스키마.

클라이언트용 응답 스키마로, pipeline용 스키마와 분리.
"""

from datetime import date
from typing import Any

from app.models.enums import PropertyType, TransactionType
from app.schemas.base import BaseSchema, GeoJSON

# ──────────────────────────── 토지 관련 ────────────────────────────


class LandInfo(BaseSchema):
    """토지특성 요약."""

    data_year: int
    jimok_name: str | None = None
    land_area: float | None = None
    use_zone_name: str | None = None
    land_use_name: str | None = None
    official_price: int | None = None


class LandUsePlanInfo(BaseSchema):
    """토지이용계획 요약."""

    data_year: int
    use_district_name: str | None = None


class ForestInfo(BaseSchema):
    """임야정보 요약."""

    data_year: int
    jimok_name: str | None = None
    area: float | None = None
    ownership_name: str | None = None
    owner_count: int | None = None


class OwnershipInfo(BaseSchema):
    """소유정보 요약."""

    ownership_type: str | None = None
    ownership_change_reason: str | None = None
    ownership_change_date: str | None = None
    owner_count: int | None = None


class OfficialPriceInfo(BaseSchema):
    """개별공시지가 요약."""

    base_year: int
    price_per_sqm: int | None = None


class LotDetailResponse(BaseSchema):
    """필지 종합 조회 응답 (GET /lots/{pnu})."""

    pnu: str
    jibun_address: str | None = None
    geometry: GeoJSON = None
    land: LandInfo | None = None
    land_use_plan: LandUsePlanInfo | None = None
    forest_info: ForestInfo | None = None
    official_price: OfficialPriceInfo | None = None
    ownerships: list[OwnershipInfo] = []


class LotSearchResult(BaseSchema):
    """필지 검색 결과."""

    pnu: str
    jibun_address: str | None = None


# ──────────────────────────── 건축물 관련 ────────────────────────────


class BuildingGeneralInfo(BaseSchema):
    """총괄표제부 요약."""

    mgm_bldrgst_pk: str
    building_name: str | None = None
    site_area: float | None = None
    building_area: float | None = None
    bcr: float | None = None
    total_floor_area: float | None = None
    far: float | None = None
    main_use_name: str | None = None
    household_count: int | None = None
    total_parking: int | None = None
    approval_date: str | None = None


class BuildingHeaderInfo(BaseSchema):
    """표제부 (동별) 요약."""

    mgm_bldrgst_pk: str
    building_name: str | None = None
    site_area: float | None = None
    building_area: float | None = None
    bcr: float | None = None
    total_floor_area: float | None = None
    far: float | None = None
    structure_name: str | None = None
    main_use_name: str | None = None
    household_count: int | None = None
    height: float | None = None
    above_ground_floors: int | None = None
    underground_floors: int | None = None
    approval_date: str | None = None


class FloorDetailInfo(BaseSchema):
    """층별개요."""

    mgm_bldrgst_pk: str
    floor_type_name: str | None = None
    floor_no: int | None = None
    main_use_name: str | None = None
    area: float | None = None


class AreaInfo(BaseSchema):
    """전유공용면적."""

    mgm_bldrgst_pk: str
    dong_name: str | None = None
    ho_name: str | None = None
    floor_no: int | None = None
    exclu_common_type: str | None = None
    area: float | None = None


class GisBuildingInfo(BaseSchema):
    """GIS 건물 요약."""

    building_id: str | None = None
    building_name: str | None = None
    use_name: str | None = None
    building_area: float | None = None
    total_floor_area: float | None = None
    site_area: float | None = None
    height: float | None = None
    above_ground_floors: int | None = None
    underground_floors: int | None = None
    approval_date: str | None = None
    geometry: GeoJSON = None


class BuildingDetailResponse(BaseSchema):
    """건축물 종합 조회 응답 (GET /buildings/{pnu})."""

    pnu: str
    general: BuildingGeneralInfo | None = None
    headers: list[BuildingHeaderInfo] = []
    floor_details: list[FloorDetailInfo] = []
    areas: list[AreaInfo] = []
    gis_buildings: list[GisBuildingInfo] = []


# ──────────────────────────── 실거래가 ────────────────────────────


class SaleResponse(BaseSchema):
    """매매 실거래가."""

    id: int
    property_type: PropertyType
    address: str | None = None
    sgg_code: str | None = None
    building_name: str | None = None
    exclusive_area: float | None = None
    land_area: float | None = None
    floor_area: float | None = None
    floor: str | None = None
    build_year: int | None = None
    transaction_date: date | None = None
    transaction_amount: int | None = None
    deal_type: str | None = None


class RentalResponse(BaseSchema):
    """전월세 실거래가."""

    id: int
    property_type: PropertyType
    transaction_type: TransactionType
    address: str | None = None
    sgg_code: str | None = None
    building_name: str | None = None
    exclusive_area: float | None = None
    land_area: float | None = None
    floor_area: float | None = None
    floor: str | None = None
    build_year: int | None = None
    transaction_date: date | None = None
    deposit: int | None = None
    monthly_rent_amount: int | None = None
    contract_period: str | None = None
    contract_type: str | None = None
    deal_type: str | None = None


class TransactionListResponse(BaseSchema):
    """실거래가 목록 응답."""

    sales: list[SaleResponse] = []
    rentals: list[RentalResponse] = []
    total_sales: int = 0
    total_rentals: int = 0


# ──────────────────────────── 통합 요약 ────────────────────────────


class LotSummary(BaseSchema):
    """필지 요약 (통합 조회용)."""

    pnu: str
    jibun_address: str | None = None


class BuildingSummary(BaseSchema):
    """건축물 요약 (통합 조회용)."""

    building_name: str | None = None
    main_use_name: str | None = None
    total_floor_area: float | None = None
    approval_date: str | None = None
    above_ground_floors: int | None = None
    underground_floors: int | None = None


class PropertySummaryResponse(BaseSchema):
    """AI 콘텐츠 생성용 통합 조회 응답 (GET /properties/{pnu}/summary)."""

    lot: LotSummary
    land: LandInfo | None = None
    official_price: OfficialPriceInfo | None = None
    building: BuildingSummary | None = None
    recent_sales: list[SaleResponse] = []
    recent_rentals: list[RentalResponse] = []


# ──────────────────────────── 지도 ────────────────────────────


class MapLotFeature(BaseSchema):
    """지도용 필지 피처."""

    pnu: str
    jibun_address: str | None = None
    geometry: GeoJSON = None


class MapBuildingFeature(BaseSchema):
    """지도용 건물 피처."""

    pnu: str
    building_id: str | None = None
    building_name: str | None = None
    use_name: str | None = None
    geometry: GeoJSON = None


class MapResponse(BaseSchema):
    """지도 데이터 응답."""

    type: str = "FeatureCollection"
    features: list[dict[str, Any]] = []
    total: int = 0
