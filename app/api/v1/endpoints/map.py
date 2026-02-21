"""지도 데이터 엔드포인트 - bbox 기반 GeoJSON 조회."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.schemas.base import wkb_to_geojson
from app.schemas.public_data import MapResponse

router = APIRouter()

# bbox 최대 면적 제한 (약 10km x 10km = 0.01도 x 0.01도 ≈ 0.0001)
MAX_BBOX_AREA = 0.01


def _validate_bbox(
    min_lng: float, min_lat: float, max_lng: float, max_lat: float
) -> None:
    """bbox 좌표 검증."""
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="경도는 -180~180 범위여야 합니다.",
        )
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="위도는 -90~90 범위여야 합니다.",
        )
    if min_lng >= max_lng or min_lat >= max_lat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min 좌표는 max 좌표보다 작아야 합니다.",
        )
    area = (max_lng - min_lng) * (max_lat - min_lat)
    if area > MAX_BBOX_AREA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="조회 범위가 너무 넓습니다. 지도를 확대해주세요.",
        )


def _lot_to_feature(lot) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "pnu": lot.pnu,
            "jimok": lot.jimok,
            "area": lot.area,
            "useZone": lot.use_zone,
            "landUse": lot.land_use,
            "officialPrice": lot.official_price,
            "ownership": lot.ownership,
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
    description="bbox 범위 내 필지를 GeoJSON FeatureCollection으로 반환합니다. "
    "필터 파라미터가 하나도 없으면 빈 결과를 반환합니다.",
)
async def get_map_lots(
    min_lng: float = Query(..., description="최소 경도"),
    min_lat: float = Query(..., description="최소 위도"),
    max_lng: float = Query(..., description="최대 경도"),
    max_lat: float = Query(..., description="최대 위도"),
    limit: int = Query(500, ge=1, le=1000, description="최대 반환 수"),
    jimok: list[str] | None = Query(None, description="지목 필터 (다중선택)"),
    min_area: float | None = Query(None, description="최소 면적(㎡)"),
    max_area: float | None = Query(None, description="최대 면적(㎡)"),
    ownership: list[str] | None = Query(None, description="소유구분 필터 (다중선택)"),
    land_use: list[str] | None = Query(None, description="이용현황 필터 (다중선택)"),
    use_zone: list[str] | None = Query(None, description="용도지역 필터 (다중선택)"),
    min_official_price: int | None = Query(None, description="최소 공시지가(원)"),
    max_official_price: int | None = Query(None, description="최대 공시지가(원)"),
    db: AsyncSession = Depends(get_db),
) -> MapResponse:
    # 필터가 하나도 없으면 빈 결과 반환 (자동 로드 방지)
    has_filters = any([
        jimok, min_area is not None, max_area is not None,
        ownership, land_use, use_zone,
        min_official_price is not None, max_official_price is not None,
    ])
    if not has_filters:
        return MapResponse(features=[], total=0)

    _validate_bbox(min_lng, min_lat, max_lng, max_lat)
    lots = await crud.get_lots_in_bbox(
        db, min_lng, min_lat, max_lng, max_lat, limit=limit,
        jimok=jimok, min_area=min_area, max_area=max_area,
        ownership=ownership, land_use=land_use, use_zone=use_zone,
        min_official_price=min_official_price, max_official_price=max_official_price,
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
    _validate_bbox(min_lng, min_lat, max_lng, max_lat)
    buildings = await crud.get_buildings_in_bbox(
        db, min_lng, min_lat, max_lng, max_lat, limit=limit
    )
    features = [_building_to_feature(bldg) for bldg in buildings]
    return MapResponse(features=features, total=len(features))
