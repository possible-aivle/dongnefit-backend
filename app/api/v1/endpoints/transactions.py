"""실거래가 엔드포인트 - 매매/전월세 조회."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import public_data as crud
from app.database import get_db
from app.models.enums import PropertyType, TransactionType
from app.schemas.public_data import (
    RentalResponse,
    SaleResponse,
    TransactionListResponse,
)

router = APIRouter()


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="실거래가 조회",
    description="시군구코드 기반으로 매매/전월세 실거래가를 조회합니다.",
)
async def get_transactions(
    sgg_code: str = Query(..., description="시군구코드 (5자리)", min_length=5, max_length=5),
    property_type: PropertyType | None = Query(None, description="부동산 유형"),
    transaction_type: TransactionType | None = Query(
        None, description="거래 유형 (전세/월세, 전월세만 해당)"
    ),
    from_date: date | None = Query(None, description="시작일 (YYYY-MM-DD)"),
    to_date: date | None = Query(None, description="종료일 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    offset = (page - 1) * limit

    sales, total_sales = await crud.get_sales(
        db,
        sgg_code,
        property_type=property_type,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )

    rentals, total_rentals = await crud.get_rentals(
        db,
        sgg_code,
        property_type=property_type,
        transaction_type=transaction_type,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )

    return TransactionListResponse(
        sales=[SaleResponse.model_validate(s) for s in sales],
        rentals=[RentalResponse.model_validate(r) for r in rentals],
        total_sales=total_sales,
        total_rentals=total_rentals,
    )
