"""DB 적재 모듈.

프로세서에서 변환된 데이터를 PostgreSQL에 bulk upsert합니다.
공공데이터 모델 타입에 따라 적절한 테이블에 삽입/업데이트합니다.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.models.administrative import AdministrativeDivision, AdministrativeEmd
from app.models.building import (
    BuildingRegisterAncillaryLot,
    BuildingRegisterArea,
    BuildingRegisterFloorDetail,
    BuildingRegisterGeneral,
    BuildingRegisterHeader,
    GisBuildingIntegrated,
)
from app.models.enums import PublicDataType
from app.models.land import (
    LandAndForestInfo,
    LandCharacteristic,
    LandUsePlan,
)
from app.models.land_ownership import LandOwnership
from app.models.lot import AncillaryLand, Lot
from app.models.spatial import RoadCenterLine, UseRegionDistrict
from app.models.transaction import (
    OfficialLandPrice,
    RealEstateRental,
    RealEstateSale,
)
from pipeline.processors.base import ProcessResult

# ── 데이터타입 ↔ 모델 매핑 ──

MODEL_MAP: dict[PublicDataType, type[SQLModel]] = {
    PublicDataType.CONTINUOUS_CADASTRAL: Lot,
    PublicDataType.ANCILLARY_LAND: AncillaryLand,
    PublicDataType.LAND_CHARACTERISTIC: LandCharacteristic,
    PublicDataType.LAND_USE_PLAN: LandUsePlan,
    PublicDataType.LAND_AND_FOREST_INFO: LandAndForestInfo,
    PublicDataType.OFFICIAL_LAND_PRICE: OfficialLandPrice,
    PublicDataType.REAL_ESTATE_SALE: RealEstateSale,
    PublicDataType.REAL_ESTATE_RENTAL: RealEstateRental,
    PublicDataType.BUILDING_REGISTER_HEADER: BuildingRegisterHeader,
    PublicDataType.BUILDING_REGISTER_GENERAL: BuildingRegisterGeneral,
    PublicDataType.BUILDING_REGISTER_FLOOR_DETAIL: BuildingRegisterFloorDetail,
    PublicDataType.BUILDING_REGISTER_AREA: BuildingRegisterArea,
    PublicDataType.BUILDING_REGISTER_ANCILLARY_LOT: BuildingRegisterAncillaryLot,
    PublicDataType.ADMINISTRATIVE_DIVISION: AdministrativeDivision,
    PublicDataType.ADMINISTRATIVE_EMD: AdministrativeEmd,
    PublicDataType.ROAD_CENTER_LINE: RoadCenterLine,
    PublicDataType.USE_REGION_DISTRICT: UseRegionDistrict,
    PublicDataType.GIS_BUILDING_INTEGRATED: GisBuildingIntegrated,
    PublicDataType.LAND_OWNERSHIP: LandOwnership,
}

# PNU 기반 테이블의 upsert 키 (unique constraint 기준)
UPSERT_KEYS: dict[PublicDataType, list[str]] = {
    PublicDataType.CONTINUOUS_CADASTRAL: ["pnu"],
    PublicDataType.LAND_CHARACTERISTIC: ["pnu", "data_year"],
    PublicDataType.LAND_USE_PLAN: ["pnu", "data_year"],
    PublicDataType.LAND_AND_FOREST_INFO: ["pnu", "data_year"],
    PublicDataType.OFFICIAL_LAND_PRICE: ["pnu", "base_year"],
    PublicDataType.ADMINISTRATIVE_DIVISION: ["code"],
    PublicDataType.ADMINISTRATIVE_EMD: ["code"],
    PublicDataType.BUILDING_REGISTER_HEADER: ["mgm_bldrgst_pk"],
    PublicDataType.BUILDING_REGISTER_GENERAL: ["mgm_bldrgst_pk"],
    PublicDataType.GIS_BUILDING_INTEGRATED: ["pnu", "building_id"],
    PublicDataType.LAND_OWNERSHIP: ["pnu", "co_owner_seq"],
    #* ROAD_CENTER_LINE, USE_REGION_DISTRICT: 단순 INSERT (UPSERT_KEYS에 없음)
}


def get_model_for_type(data_type: PublicDataType) -> type[SQLModel]:
    """데이터 타입에 대응하는 SQLModel 클래스를 반환합니다."""
    if data_type not in MODEL_MAP:
        raise ValueError(f"매핑되지 않은 데이터 타입: {data_type}")
    return MODEL_MAP[data_type]


def get_table_name(data_type: PublicDataType) -> str:
    """데이터 타입에 대응하는 테이블명을 반환합니다."""
    model = get_model_for_type(data_type)
    return model.__tablename__  # type: ignore[attr-defined]


def get_all_public_tables() -> dict[str, PublicDataType]:
    """모든 공공데이터 테이블명 → 데이터타입 매핑을 반환합니다."""
    return {get_table_name(dt): dt for dt in MODEL_MAP}


# ── Bulk Insert ──


def _build_val_expr(col: str) -> str:
    """컬럼에 맞는 SQL 값 표현식을 반환합니다.

    geometry 컬럼은 WKT 문자열을 PostGIS Geometry로 변환합니다.
    """
    if col == "geometry":
        return f"ST_GeomFromText(:{col}, 4326)"
    return f":{col}"


async def bulk_insert(
    session: AsyncSession,
    table_name: str,
    records: list[dict[str, Any]],
    batch_size: int = 500,
) -> int:
    """raw dict 리스트를 지정 테이블에 bulk insert합니다."""
    if not records:
        return 0

    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        columns = list(batch[0].keys())
        col_str = ", ".join(columns)
        val_str = ", ".join(_build_val_expr(col) for col in columns)

        await session.execute(
            text(f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str})"),  # noqa: S608
            batch,
        )
        total += len(batch)

    await session.commit()
    return total


# ── Bulk Upsert ──


async def bulk_upsert(
    session: AsyncSession,
    data_type: PublicDataType,
    records: list[dict[str, Any]],
    batch_size: int = 500,
) -> ProcessResult:
    """데이터를 bulk upsert합니다.

    UPSERT_KEYS에 정의된 키 기준으로 중복 시 업데이트, 없으면 삽입합니다.
    UPSERT_KEYS에 없는 타입은 단순 INSERT합니다.
    """
    if not records:
        return ProcessResult()

    table_name = get_table_name(data_type)
    upsert_keys = UPSERT_KEYS.get(data_type)

    if upsert_keys is None:
        # 단순 INSERT (실거래가 등 중복키 없는 경우)
        count = await bulk_insert(session, table_name, records, batch_size)
        return ProcessResult(inserted=count)

    # UPSERT (ON CONFLICT DO UPDATE)
    inserted = 0
    updated = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        columns = list(batch[0].keys())
        col_str = ", ".join(columns)
        val_str = ", ".join(_build_val_expr(col) for col in columns)
        conflict_str = ", ".join(upsert_keys)

        # 업데이트할 컬럼 (키 제외)
        update_cols = [c for c in columns if c not in upsert_keys]
        if update_cols:
            set_str = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
            sql = (
                f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str}) "
                f"ON CONFLICT ({conflict_str}) DO UPDATE SET {set_str}"
            )
        else:
            sql = (
                f"INSERT INTO {table_name} ({col_str}) VALUES ({val_str}) "
                f"ON CONFLICT ({conflict_str}) DO NOTHING"
            )

        result = await session.execute(text(sql), batch)  # noqa: S608
        row_count = result.rowcount if result.rowcount else 0
        inserted += row_count

    await session.commit()

    return ProcessResult(
        inserted=inserted,
        updated=updated,
    )
