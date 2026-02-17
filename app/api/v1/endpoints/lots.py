"""필지(Lot) 엔드포인트 - 검색 + 종합 조회."""

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.public_data import (
    ForestInfo,
    LandInfo,
    LandUsePlanInfo,
    LotDetailResponse,
    LotSearchResult,
    OfficialPriceInfo,
    OwnershipInfo,
)

router = APIRouter()

PNU_PATTERN = re.compile(r"^\d{19}$")


def _validate_pnu(pnu: str) -> None:
    """PNU 형식 검증 (19자리 숫자)."""
    if not PNU_PATTERN.match(pnu):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNU는 19자리 숫자여야 합니다.",
        )


@router.get(
    "/search",
    response_model=PaginatedResponse[LotSearchResult] | list[LotSearchResult],
    summary="필지 검색",
    description="좌표 또는 시군구코드로 필지를 검색합니다.",
)
async def search_lots(
    db: AsyncSession = Depends(get_db),
    lat: float | None = Query(None, description="위도 (좌표 검색)"),
    lng: float | None = Query(None, description="경도 (좌표 검색)"),
    sgg_code: str | None = Query(None, description="시군구코드 (5자리)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[LotSearchResult] | list[LotSearchResult]:
    # 좌표 검색
    if lat is not None and lng is not None:
        lot = await crud.search_lot_by_point(db, lat, lng)
        if not lot:
            return []
        return [LotSearchResult.model_validate(lot)]

    # 시군구코드 검색 (페이지네이션)
    if sgg_code:
        offset = (page - 1) * limit
        lots, total = await crud.search_lots_by_sgg(
            db, sgg_code, offset=offset, limit=limit
        )
        return PaginatedResponse(
            data=[LotSearchResult.model_validate(lot) for lot in lots],
            pagination=PaginationMeta(
                page=page,
                limit=limit,
                total=total,
                total_pages=(total + limit - 1) // limit if total else 0,
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="lat+lng 또는 sgg_code 중 하나를 지정해야 합니다.",
    )


@router.get(
    "/{pnu}",
    response_model=LotDetailResponse,
    summary="필지 종합 조회",
    description="PNU로 필지의 토지특성, 이용계획, 임야정보, 공시지가, 소유정보를 종합 조회합니다.",
)
async def get_lot_detail(
    pnu: str,
    db: AsyncSession = Depends(get_db),
) -> LotDetailResponse:
    _validate_pnu(pnu)

    lot = await crud.get_lot_by_pnu(db, pnu)
    if not lot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="필지를 찾을 수 없습니다.",
        )

    land, land_use, forest, price, ownerships = await asyncio.gather(
        crud.get_land_characteristic(db, pnu),
        crud.get_land_use_plan(db, pnu),
        crud.get_land_forest_info(db, pnu),
        crud.get_official_land_price(db, pnu),
        crud.get_land_ownerships(db, pnu),
    )

    return LotDetailResponse(
        pnu=lot.pnu,
        geometry=lot.geometry,
        land=LandInfo.model_validate(land) if land else None,
        land_use_plan=LandUsePlanInfo.model_validate(land_use) if land_use else None,
        forest_info=ForestInfo.model_validate(forest) if forest else None,
        official_price=OfficialPriceInfo.model_validate(price) if price else None,
        ownerships=[OwnershipInfo.model_validate(o) for o in ownerships],
    )
