"""Neighborhood endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AdminUser
from app.crud.neighborhood import neighborhood as neighborhood_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.neighborhood import (
    LocationQuery,
    NeighborhoodCreate,
    NeighborhoodQuery,
    NeighborhoodResponse,
    NeighborhoodUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[NeighborhoodResponse],
    summary="List neighborhoods",
    description="List all neighborhoods with pagination and filtering",
)
async def list_neighborhoods(
    query: NeighborhoodQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[NeighborhoodResponse]:
    """List neighborhoods with filtering and pagination."""
    neighborhoods, total = await neighborhood_crud.get_multi_with_query(db, query=query)

    return PaginatedResponse(
        data=[NeighborhoodResponse.model_validate(n) for n in neighborhoods],
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/cities",
    response_model=list[str],
    summary="List cities",
    description="Get list of all unique cities",
)
async def list_cities(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get list of unique cities."""
    return await neighborhood_crud.get_cities(db)


@router.get(
    "/districts",
    response_model=list[str],
    summary="List districts",
    description="Get list of districts in a city",
)
async def list_districts(
    city: str,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get list of districts in a city."""
    return await neighborhood_crud.get_districts(db, city)


@router.post(
    "/search-by-location",
    response_model=list[NeighborhoodResponse],
    summary="Search by location",
    description="Find neighborhoods near a geographic location",
)
async def search_by_location(
    query: LocationQuery,
    db: AsyncSession = Depends(get_db),
) -> list[NeighborhoodResponse]:
    """Find neighborhoods near a location."""
    neighborhoods = await neighborhood_crud.search_by_location(
        db,
        lat=query.lat,
        lng=query.lng,
        radius_km=query.radius_km,
    )
    return [NeighborhoodResponse.model_validate(n) for n in neighborhoods]


@router.get(
    "/{neighborhood_id}",
    response_model=NeighborhoodResponse,
    summary="Get neighborhood",
    description="Get a specific neighborhood by ID",
)
async def get_neighborhood(
    neighborhood_id: int,
    db: AsyncSession = Depends(get_db),
) -> NeighborhoodResponse:
    """Get a neighborhood by ID."""
    neighborhood = await neighborhood_crud.get(db, neighborhood_id)
    if not neighborhood:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동네를 찾을 수 없습니다",
        )
    return NeighborhoodResponse.model_validate(neighborhood)


@router.post(
    "",
    response_model=NeighborhoodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create neighborhood",
    description="Create a new neighborhood (Admin only)",
)
async def create_neighborhood(
    neighborhood_in: NeighborhoodCreate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> NeighborhoodResponse:
    """Create a new neighborhood."""
    neighborhood = await neighborhood_crud.create_neighborhood(db, obj_in=neighborhood_in)
    return NeighborhoodResponse.model_validate(neighborhood)


@router.patch(
    "/{neighborhood_id}",
    response_model=NeighborhoodResponse,
    summary="Update neighborhood",
    description="Update a neighborhood (Admin only)",
)
async def update_neighborhood(
    neighborhood_id: int,
    neighborhood_in: NeighborhoodUpdate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> NeighborhoodResponse:
    """Update a neighborhood."""
    neighborhood = await neighborhood_crud.get(db, neighborhood_id)
    if not neighborhood:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동네를 찾을 수 없습니다",
        )

    neighborhood = await neighborhood_crud.update_neighborhood(
        db, db_obj=neighborhood, obj_in=neighborhood_in
    )
    return NeighborhoodResponse.model_validate(neighborhood)


@router.delete(
    "/{neighborhood_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete neighborhood",
    description="Delete a neighborhood (Admin only)",
)
async def delete_neighborhood(
    neighborhood_id: int,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a neighborhood."""
    neighborhood = await neighborhood_crud.get(db, neighborhood_id)
    if not neighborhood:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="동네를 찾을 수 없습니다",
        )

    await neighborhood_crud.delete(db, id=neighborhood_id)
