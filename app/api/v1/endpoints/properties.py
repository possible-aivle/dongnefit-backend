"""통합 요약 엔드포인트 - AI 콘텐츠 생성용."""

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.public_data import (
    BuildingSummary,
    LandInfo,
    LotSummary,
    OfficialPriceInfo,
    PropertySummaryResponse,
    RentalResponse,
    SaleResponse,
)

router = APIRouter()

PNU_PATTERN = re.compile(r"^\d{19}$")


@router.get(
    "/{pnu}/summary",
    response_model=PropertySummaryResponse,
    summary="부동산 통합 요약 조회",
    description="PNU로 필지, 토지, 건축물, 최근 실거래가를 통합 조회합니다. AI 콘텐츠 생성에 최적화.",
)
async def get_property_summary(
    pnu: str,
    db: AsyncSession = Depends(get_db),
) -> PropertySummaryResponse:
    if not PNU_PATTERN.match(pnu):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNU는 19자리 숫자여야 합니다.",
        )

    lot = await crud.get_lot_by_pnu(db, pnu)
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="필지를 찾을 수 없습니다.",
        )

    # PNU에서 sgg_code 추출 (앞 5자리)
    sgg_code = pnu[:5]

    # 6개 쿼리를 병렬 실행
    land, price, general, headers, recent_sales, recent_rentals = await asyncio.gather(
        crud.get_land_characteristic(db, pnu),
        crud.get_official_land_price(db, pnu),
        crud.get_building_general(db, pnu),
        crud.get_building_headers(db, pnu),
        crud.get_recent_sales_by_sgg(db, sgg_code, limit=5),
        crud.get_recent_rentals_by_sgg(db, sgg_code, limit=5),
    )

    building_summary = None
    if general:
        building_summary = BuildingSummary(
            building_name=general.building_name,
            main_use_name=general.main_use_name,
            total_floor_area=general.total_floor_area,
            approval_date=general.approval_date,
        )
        # 표제부에서 층수 정보 보완
        if headers:
            first = headers[0]
            building_summary.above_ground_floors = first.above_ground_floors
            building_summary.underground_floors = first.underground_floors

    return PropertySummaryResponse(
        lot=LotSummary(pnu=lot.pnu),
        land=LandInfo.model_validate(land) if land else None,
        official_price=OfficialPriceInfo.model_validate(price) if price else None,
        building=building_summary,
        recent_sales=[SaleResponse.model_validate(s) for s in recent_sales],
        recent_rentals=[RentalResponse.model_validate(r) for r in recent_rentals],
    )
