"""필지(Lot) 엔드포인트 - 검색 + 종합 조회."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.lot import LotFilterOptions
from app.schemas.public_data import (
    AncillaryLotItem,
    LotDetailResponse,
    LotSearchResult,
    OfficialPriceItem,
    UsePlanItem,
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
    "/filter-options",
    response_model=LotFilterOptions,
    summary="필지 필터 옵션 조회",
    description="필터에 사용할 지목, 소유구분, 용도지역, 이용현황의 고유값 목록을 반환합니다.",
)
async def get_lot_filter_options(
    db: AsyncSession = Depends(get_db),
) -> LotFilterOptions:
    options = await crud.get_lot_filter_options(db)
    return LotFilterOptions(**options)


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
    description="PNU로 필지의 토지특성, 이용계획, 공시지가, 소유정보를 종합 조회합니다.",
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

    return LotDetailResponse(
        pnu=lot.pnu,
        address=lot.address,
        geometry=lot.geometry,
        jimok=lot.jimok,
        area=lot.area,
        use_zone=lot.use_zone,
        land_use=lot.land_use,
        official_price=lot.official_price,
        ownership=lot.ownership,
        owner_count=lot.owner_count,
        use_plans=[
            UsePlanItem.model_validate(p) for p in (lot.use_plans or [])
        ],
        official_prices=[
            OfficialPriceItem.model_validate(p) for p in (lot.official_prices or [])
        ],
        ancillary_lots=[
            AncillaryLotItem.model_validate(a) for a in (lot.ancillary_lots or [])
        ],
    )
