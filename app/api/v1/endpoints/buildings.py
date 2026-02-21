"""건축물 엔드포인트 - 종합 조회."""

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.public_data import (
    AreaInfo,
    BuildingDetailResponse,
    BuildingGeneralInfo,
    BuildingHeaderInfo,
    FloorDetailInfo,
    GisBuildingInfo,
)

router = APIRouter()

PNU_PATTERN = re.compile(r"^\d{19}$")


@router.get(
    "/{pnu}",
    response_model=BuildingDetailResponse,
    summary="건축물 종합 조회",
    description="PNU로 건축물의 총괄표제부, 표제부, 층별개요, 면적, GIS 건물정보를 종합 조회합니다.",
)
async def get_building_detail(
    pnu: str,
    db: AsyncSession = Depends(get_db),
) -> BuildingDetailResponse:
    if not PNU_PATTERN.match(pnu):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PNU는 19자리 숫자여야 합니다.",
        )

    # 모든 건축물 데이터를 병렬 조회
    general, headers, gis_buildings, floor_details, areas = await asyncio.gather(
        crud.get_building_general(db, pnu),
        crud.get_building_headers(db, pnu),
        crud.get_gis_buildings(db, pnu),
        crud.get_building_floor_details(db, pnu),
        crud.get_building_areas(db, pnu),
    )

    if not general and not headers and not gis_buildings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 필지의 건축물 정보를 찾을 수 없습니다.",
        )

    return BuildingDetailResponse(
        pnu=pnu,
        general=BuildingGeneralInfo.model_validate(general) if general else None,
        headers=[BuildingHeaderInfo.model_validate(h) for h in headers],
        floor_details=[FloorDetailInfo.model_validate(f) for f in floor_details],
        areas=[AreaInfo.model_validate(a) for a in areas],
        gis_buildings=[GisBuildingInfo.model_validate(g) for g in gis_buildings],
    )
