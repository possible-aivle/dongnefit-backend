"""공공데이터 CRUD - PNU 기반 조회 함수들."""

from datetime import date

from geoalchemy2.functions import (
    ST_Contains,
    ST_Intersects,
    ST_MakeEnvelope,
    ST_MakePoint,
    ST_SetSRID,
)
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.building import (
    BuildingRegisterArea,
    BuildingRegisterFloorDetail,
    BuildingRegisterGeneral,
    BuildingRegisterHeader,
    GisBuildingIntegrated,
)
from app.models.enums import PropertyType, TransactionType
from app.models.land import LandAndForestInfo, LandCharacteristic, LandUsePlan
from app.models.land_ownership import LandOwnership
from app.models.lot import Lot
from app.models.transaction import OfficialLandPrice, RealEstateRental, RealEstateSale

# ──────────────────────────── 필지(Lot) ────────────────────────────


async def get_lot_by_pnu(db: AsyncSession, pnu: str) -> Lot | None:
    result = await db.execute(select(Lot).where(Lot.pnu == pnu))
    return result.scalar_one_or_none()


async def search_lots_by_address(
    db: AsyncSession, keyword: str, *, limit: int = 20
) -> list[Lot]:
    stmt = (
        select(Lot)
        .where(Lot.jibun_address.ilike(f"%{keyword}%"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def search_lot_by_point(
    db: AsyncSession, lat: float, lng: float
) -> Lot | None:
    point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
    stmt = select(Lot).where(ST_Contains(Lot.geometry, point)).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def search_lots_by_sgg(
    db: AsyncSession, sgg_code: str, *, offset: int = 0, limit: int = 20
) -> tuple[list[Lot], int]:
    prefix = sgg_code[:5]
    base = select(Lot).where(Lot.pnu.startswith(prefix))
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = base.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


# ──────────────────────────── 토지 ────────────────────────────


async def get_land_characteristic(
    db: AsyncSession, pnu: str
) -> LandCharacteristic | None:
    stmt = (
        select(LandCharacteristic)
        .where(LandCharacteristic.pnu == pnu)
        .order_by(desc(LandCharacteristic.data_year))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_land_use_plan(db: AsyncSession, pnu: str) -> LandUsePlan | None:
    stmt = (
        select(LandUsePlan)
        .where(LandUsePlan.pnu == pnu)
        .order_by(desc(LandUsePlan.data_year))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_land_forest_info(
    db: AsyncSession, pnu: str
) -> LandAndForestInfo | None:
    stmt = (
        select(LandAndForestInfo)
        .where(LandAndForestInfo.pnu == pnu)
        .order_by(desc(LandAndForestInfo.data_year))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_official_land_price(
    db: AsyncSession, pnu: str
) -> OfficialLandPrice | None:
    stmt = (
        select(OfficialLandPrice)
        .where(OfficialLandPrice.pnu == pnu)
        .order_by(desc(OfficialLandPrice.base_year))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_land_ownerships(
    db: AsyncSession, pnu: str
) -> list[LandOwnership]:
    stmt = select(LandOwnership).where(LandOwnership.pnu == pnu)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────── 건축물 ────────────────────────────


async def get_building_general(
    db: AsyncSession, pnu: str
) -> BuildingRegisterGeneral | None:
    stmt = (
        select(BuildingRegisterGeneral)
        .where(BuildingRegisterGeneral.pnu == pnu)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_building_headers(
    db: AsyncSession, pnu: str
) -> list[BuildingRegisterHeader]:
    stmt = select(BuildingRegisterHeader).where(
        BuildingRegisterHeader.pnu == pnu
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_building_floor_details(
    db: AsyncSession, pnu: str
) -> list[BuildingRegisterFloorDetail]:
    stmt = select(BuildingRegisterFloorDetail).where(
        BuildingRegisterFloorDetail.pnu == pnu
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_building_areas(
    db: AsyncSession, pnu: str
) -> list[BuildingRegisterArea]:
    stmt = select(BuildingRegisterArea).where(
        BuildingRegisterArea.pnu == pnu
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_gis_buildings(
    db: AsyncSession, pnu: str
) -> list[GisBuildingIntegrated]:
    stmt = select(GisBuildingIntegrated).where(
        GisBuildingIntegrated.pnu == pnu
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────── 실거래가 ────────────────────────────


async def get_sales(
    db: AsyncSession,
    sgg_code: str,
    *,
    property_type: PropertyType | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[RealEstateSale], int]:
    base = select(RealEstateSale).where(RealEstateSale.sgg_code == sgg_code)
    if property_type:
        base = base.where(RealEstateSale.property_type == property_type)
    if from_date:
        base = base.where(RealEstateSale.transaction_date >= from_date)
    if to_date:
        base = base.where(RealEstateSale.transaction_date <= to_date)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(desc(RealEstateSale.transaction_date)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_rentals(
    db: AsyncSession,
    sgg_code: str,
    *,
    property_type: PropertyType | None = None,
    transaction_type: TransactionType | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[RealEstateRental], int]:
    base = select(RealEstateRental).where(RealEstateRental.sgg_code == sgg_code)
    if property_type:
        base = base.where(RealEstateRental.property_type == property_type)
    if transaction_type:
        base = base.where(RealEstateRental.transaction_type == transaction_type)
    if from_date:
        base = base.where(RealEstateRental.transaction_date >= from_date)
    if to_date:
        base = base.where(RealEstateRental.transaction_date <= to_date)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(desc(RealEstateRental.transaction_date)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_recent_sales_by_sgg(
    db: AsyncSession, sgg_code: str, *, limit: int = 5
) -> list[RealEstateSale]:
    stmt = (
        select(RealEstateSale)
        .where(RealEstateSale.sgg_code == sgg_code)
        .order_by(desc(RealEstateSale.transaction_date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_recent_rentals_by_sgg(
    db: AsyncSession, sgg_code: str, *, limit: int = 5
) -> list[RealEstateRental]:
    stmt = (
        select(RealEstateRental)
        .where(RealEstateRental.sgg_code == sgg_code)
        .order_by(desc(RealEstateRental.transaction_date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────── 지도 (bbox) ────────────────────────────


async def get_lots_in_bbox(
    db: AsyncSession,
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
    *,
    limit: int = 500,
) -> list[Lot]:
    envelope = ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    stmt = (
        select(Lot)
        .where(ST_Intersects(Lot.geometry, envelope))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_buildings_in_bbox(
    db: AsyncSession,
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
    *,
    limit: int = 500,
) -> list[GisBuildingIntegrated]:
    envelope = ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    stmt = (
        select(GisBuildingIntegrated)
        .where(ST_Intersects(GisBuildingIntegrated.geometry, envelope))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
