"""공시지가 예측용 데이터 추출 CRUD."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.building import BuildingRegisterGeneral
from app.models.lot import Lot
from app.models.transaction import RealEstateRental, RealEstateSale

# asyncpg 파라미터 한계 (32767)를 넘지 않도록 배치 크기 제한
_BATCH_SIZE = 30000


async def get_lots_with_price_history(
    db: AsyncSession,
    *,
    min_years: int = 1,
    sgg_code: str | None = None,
) -> list[Lot]:
    """공시지가 이력이 min_years 이상인 필지 목록 조회.

    훈련 데이터 추출용. official_prices JSONB 배열 길이로 필터.
    """
    stmt = select(Lot).where(
        Lot.official_prices.is_not(None),
        text(f"jsonb_array_length(official_prices) >= {min_years}"),
    )
    if sgg_code:
        stmt = stmt.where(Lot.pnu.startswith(sgg_code))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_buildings_for_pnus(
    db: AsyncSession,
    pnus: list[str],
) -> dict[str, dict[str, Any]]:
    """배치 BuildingRegisterGeneral 조회 → {pnu: building_dict}.

    PNU가 많을 경우 배치 분할하여 asyncpg 파라미터 한계 회피.
    """
    if not pnus:
        return {}

    bld_map: dict[str, dict[str, Any]] = {}

    for i in range(0, len(pnus), _BATCH_SIZE):
        batch = pnus[i : i + _BATCH_SIZE]
        stmt = select(BuildingRegisterGeneral).where(
            BuildingRegisterGeneral.pnu.in_(batch)
        )
        result = await db.execute(stmt)
        for b in result.scalars().all():
            if b.pnu not in bld_map:
                bld_map[b.pnu] = {
                    "total_floor_area": b.total_floor_area,
                    "bcr": b.bcr,
                    "far": b.far,
                    "above_ground_floors": None,
                    "approval_date": b.approval_date,
                }

    return bld_map


async def get_sgg_transaction_stats(
    db: AsyncSession,
    sgg_codes: list[str],
) -> dict[str, dict[str, float]]:
    """시군구별 최근 2년 매매/전세 통계 집계.

    Returns:
        {sgg_code: {"avg_sale_price": ..., "sale_volume": ..., "avg_deposit": ...}}
    """
    if not sgg_codes:
        return {}

    two_years_ago = date.today() - timedelta(days=730)

    sale_stmt = (
        select(
            RealEstateSale.sgg_code,
            func.avg(RealEstateSale.transaction_amount).label("avg_price"),
            func.count().label("volume"),
        )
        .where(
            RealEstateSale.sgg_code.in_(sgg_codes),
            RealEstateSale.transaction_date >= two_years_ago,
            RealEstateSale.transaction_amount.is_not(None),
        )
        .group_by(RealEstateSale.sgg_code)
    )
    sale_result = await db.execute(sale_stmt)
    sale_rows = {row.sgg_code: row for row in sale_result.all()}

    rental_stmt = (
        select(
            RealEstateRental.sgg_code,
            func.avg(RealEstateRental.deposit).label("avg_deposit"),
        )
        .where(
            RealEstateRental.sgg_code.in_(sgg_codes),
            RealEstateRental.transaction_date >= two_years_ago,
            RealEstateRental.deposit.is_not(None),
        )
        .group_by(RealEstateRental.sgg_code)
    )
    rental_result = await db.execute(rental_stmt)
    rental_rows = {row.sgg_code: row for row in rental_result.all()}

    stats: dict[str, dict[str, float]] = {}
    for code in sgg_codes:
        sale = sale_rows.get(code)
        rental = rental_rows.get(code)
        stats[code] = {
            "avg_sale_price": float(sale.avg_price) if sale else 0.0,
            "sale_volume": float(sale.volume) if sale else 0.0,
            "avg_deposit": float(rental.avg_deposit) if rental else 0.0,
        }
    return stats


async def get_lots_by_pnus(
    db: AsyncSession,
    pnus: list[str],
) -> list[Lot]:
    """PNU 리스트로 lots 조회 (official_prices 유무 무관).

    CSV 기반 학습 시, CSV에서 PNU를 추출한 뒤 DB의 토지 특성을 조회하는 데 사용.
    """
    if not pnus:
        return []

    lots: list[Lot] = []
    for i in range(0, len(pnus), _BATCH_SIZE):
        batch = pnus[i : i + _BATCH_SIZE]
        stmt = select(Lot).where(Lot.pnu.in_(batch))
        result = await db.execute(stmt)
        lots.extend(result.scalars().all())

    return lots


async def get_sgg_price_stats(
    db: AsyncSession,
    sgg_codes: list[str],
) -> dict[str, dict[str, float]]:
    """시군구별 공시지가 통계 (lots.official_price flat 컬럼 기반).

    Returns:
        {sgg_code: {"median_price": float, "mean_price": float, "count": int}}
    """
    if not sgg_codes:
        return {}

    stats: dict[str, dict[str, float]] = {}

    for code in sgg_codes:
        stmt = (
            select(
                func.avg(Lot.official_price).label("mean_price"),
                func.count().label("cnt"),
                func.percentile_cont(0.5).within_group(Lot.official_price).label("median_price"),
            )
            .where(
                Lot.pnu.startswith(code),
                Lot.official_price.is_not(None),
                Lot.official_price > 0,
            )
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row and row.cnt > 0:
            stats[code] = {
                "median_price": float(row.median_price or 0),
                "mean_price": float(row.mean_price or 0),
                "count": int(row.cnt),
            }
        else:
            stats[code] = {"median_price": 0.0, "mean_price": 0.0, "count": 0}

    return stats


async def get_sgg_growth_rates(
    db: AsyncSession,
    sgg_codes: list[str],
) -> dict[str, float]:
    """시군구별 연간 성장률 추정 (실거래가 CAGR 기반).

    최근 3년간 연도별 평균 실거래가를 비교하여 CAGR 계산.

    Returns:
        {sgg_code: 0.05}  (5% 연간 성장)
    """
    if not sgg_codes:
        return {}

    three_years_ago = date.today() - timedelta(days=1095)

    stmt = (
        select(
            RealEstateSale.sgg_code,
            func.extract("year", RealEstateSale.transaction_date).label("yr"),
            func.avg(RealEstateSale.transaction_amount).label("avg_price"),
        )
        .where(
            RealEstateSale.sgg_code.in_(sgg_codes),
            RealEstateSale.transaction_date >= three_years_ago,
            RealEstateSale.transaction_amount.is_not(None),
            RealEstateSale.transaction_amount > 0,
        )
        .group_by(RealEstateSale.sgg_code, literal_column("yr"))
        .order_by(RealEstateSale.sgg_code, literal_column("yr"))
    )
    result = await db.execute(stmt)
    rows = result.all()

    # sgg별 연도별 평균가 수집
    sgg_yearly: dict[str, dict[int, float]] = {}
    for row in rows:
        code = row.sgg_code
        yr = int(row.yr)
        if code not in sgg_yearly:
            sgg_yearly[code] = {}
        sgg_yearly[code][yr] = float(row.avg_price)

    rates: dict[str, float] = {}
    for code in sgg_codes:
        yearly = sgg_yearly.get(code, {})
        if len(yearly) >= 2:
            years = sorted(yearly.keys())
            first_price = yearly[years[0]]
            last_price = yearly[years[-1]]
            n_years = years[-1] - years[0]
            if first_price > 0 and n_years > 0:
                cagr = (last_price / first_price) ** (1.0 / n_years) - 1.0
                rates[code] = round(cagr, 4)
            else:
                rates[code] = 0.03
        else:
            rates[code] = 0.03  # 데이터 부족 시 기본값

    return rates
