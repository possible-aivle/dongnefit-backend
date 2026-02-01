"""Report endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AdminUser, CurrentUser
from app.crud.report import report as report_crud
from app.crud.report import report_category as category_crud
from app.crud.report import report_review as review_crud
from app.database import get_db
from app.schemas.base import PaginatedResponse, PaginationMeta
from app.schemas.report import (
    ReportCategoryCreate,
    ReportCategoryResponse,
    ReportCreate,
    ReportQuery,
    ReportResponse,
    ReportReviewCreate,
    ReportReviewResponse,
    ReportUpdate,
)

router = APIRouter()


# === Categories ===


@router.get(
    "/categories",
    response_model=list[ReportCategoryResponse],
    summary="List report categories",
    description="Get all report categories",
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[ReportCategoryResponse]:
    """List all report categories."""
    categories = await category_crud.get_all(db)
    return [ReportCategoryResponse.model_validate(c) for c in categories]


@router.post(
    "/categories",
    response_model=ReportCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new report category (Admin only)",
)
async def create_category(
    category_in: ReportCategoryCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportCategoryResponse:
    """Create a new category."""
    existing = await category_crud.get_by_slug(db, category_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 슬러그입니다",
        )

    category = await category_crud.create(db, obj_in=category_in.model_dump())
    return ReportCategoryResponse.model_validate(category)


# === Reports ===


@router.get(
    "",
    response_model=PaginatedResponse[ReportResponse],
    summary="List reports",
    description="List reports with pagination and filtering",
)
async def list_reports(
    query: ReportQuery = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportResponse]:
    """List reports with filtering and pagination."""
    reports, total = await report_crud.get_multi_with_query(db, query=query)

    return PaginatedResponse(
        data=[ReportResponse.model_validate(r) for r in reports],
        pagination=PaginationMeta(
            page=query.page,
            limit=query.limit,
            total=total,
            total_pages=(total + query.limit - 1) // query.limit,
        ),
    )


@router.get(
    "/published",
    response_model=PaginatedResponse[ReportResponse],
    summary="List published reports",
    description="List only published reports",
)
async def list_published_reports(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportResponse]:
    """List published reports."""
    offset = (page - 1) * limit
    reports, total = await report_crud.get_published(db, offset=offset, limit=limit)

    return PaginatedResponse(
        data=[ReportResponse.model_validate(r) for r in reports],
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report",
    description="Get a specific report by ID",
)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Get a report by ID."""
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )
    return ReportResponse.model_validate(report)


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
    description="Create a new report (Admin only)",
)
async def create_report(
    report_in: ReportCreate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Create a new report."""
    report = await report_crud.create_report(
        db, author_id=admin.id, obj_in=report_in
    )
    return ReportResponse.model_validate(report)


@router.patch(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Update report",
    description="Update a report (Admin only)",
)
async def update_report(
    report_id: int,
    report_in: ReportUpdate,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Update a report."""
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )

    report = await report_crud.update_report(db, db_obj=report, obj_in=report_in)
    return ReportResponse.model_validate(report)


@router.post(
    "/{report_id}/publish",
    response_model=ReportResponse,
    summary="Publish report",
    description="Publish a report (Admin only)",
)
async def publish_report(
    report_id: int,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Publish a report."""
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )

    report = await report_crud.publish(db, db_obj=report)
    return ReportResponse.model_validate(report)


@router.post(
    "/{report_id}/archive",
    response_model=ReportResponse,
    summary="Archive report",
    description="Archive a report (Admin only)",
)
async def archive_report(
    report_id: int,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Archive a report."""
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )

    report = await report_crud.archive(db, db_obj=report)
    return ReportResponse.model_validate(report)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report",
    description="Delete a report (Admin only)",
)
async def delete_report(
    report_id: int,
    admin: AdminUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a report."""
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )

    await report_crud.delete(db, id=report_id)


# === Reviews ===


@router.get(
    "/{report_id}/reviews",
    response_model=list[ReportReviewResponse],
    summary="List report reviews",
    description="Get reviews for a report",
)
async def list_report_reviews(
    report_id: int,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[ReportReviewResponse]:
    """List reviews for a report."""
    offset = (page - 1) * limit
    reviews, _ = await review_crud.get_by_report(
        db, report_id=report_id, offset=offset, limit=limit
    )
    return [ReportReviewResponse.model_validate(r) for r in reviews]


@router.post(
    "/{report_id}/reviews",
    response_model=ReportReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    description="Create a review for a report",
)
async def create_report_review(
    report_id: int,
    review_in: ReportReviewCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> ReportReviewResponse:
    """Create a review for a report."""
    # Check if report exists
    report = await report_crud.get(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="리포트를 찾을 수 없습니다",
        )

    # Check if user already reviewed
    existing = await review_crud.get_user_review(
        db, report_id=report_id, user_id=current_user.id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 리뷰를 작성했습니다",
        )

    review = await review_crud.create_review(
        db, report_id=report_id, user_id=current_user.id, obj_in=review_in
    )
    return ReportReviewResponse.model_validate(review)
