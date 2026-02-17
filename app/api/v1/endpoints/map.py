"""지도 데이터 엔드포인트 - bbox 기반 GeoJSON 조회."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.base import wkb_to_geojson
from app.schemas.public_data import MapResponse

router = APIRouter()


def _lot_to_feature(lot) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "pnu": lot.pnu,
            "jibunAddress": lot.jibun_address,
        },
        "geometry": wkb_to_geojson(lot.geometry),
    }


def _building_to_feature(bldg) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "pnu": bldg.pnu,
            "buildingId": bldg.building_id,
            "buildingName": bldg.building_name,
            "useName": bldg.use_name,
        },
        "geometry": wkb_to_geojson(bldg.geometry),
    }


@router.get(
    "/lots",
    response_model=MapResponse,
    summary="지도용 필지 조회",
    description="bbox 범위 내 필지를 GeoJSON FeatureCollection으로 반환합니다.",
)
async def get_map_lots(
    min_lng: float = Query(..., description="최소 경도"),
    min_lat: float = Query(..., description="최소 위도"),
    max_lng: float = Query(..., description="최대 경도"),
    max_lat: float = Query(..., description="최대 위도"),
    limit: int = Query(500, ge=1, le=1000, description="최대 반환 수"),
    db: AsyncSession = Depends(get_db),
) -> MapResponse:
    lots = await crud.get_lots_in_bbox(
        db, min_lng, min_lat, max_lng, max_lat, limit=limit
    )
    features = [_lot_to_feature(lot) for lot in lots]
    return MapResponse(features=features, total=len(features))


@router.get(
    "/buildings",
    response_model=MapResponse,
    summary="지도용 건물 조회",
    description="bbox 범위 내 건물을 GeoJSON FeatureCollection으로 반환합니다.",
)
async def get_map_buildings(
    min_lng: float = Query(..., description="최소 경도"),
    min_lat: float = Query(..., description="최소 위도"),
    max_lng: float = Query(..., description="최대 경도"),
    max_lat: float = Query(..., description="최대 위도"),
    limit: int = Query(500, ge=1, le=1000, description="최대 반환 수"),
    db: AsyncSession = Depends(get_db),
) -> MapResponse:
    buildings = await crud.get_buildings_in_bbox(
        db, min_lng, min_lat, max_lng, max_lat, limit=limit
    )
    features = [_building_to_feature(bldg) for bldg in buildings]
    return MapResponse(features=features, total=len(features))
