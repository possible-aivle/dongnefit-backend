"""CRUD operations for reports."""

from datetime import datetime
from typing import Any

from geoalchemy2.elements import WKBElement
from shapely.geometry import shape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, func, or_, select

from app.crud.base import CRUDBase
from app.models.report import Report, ReportCategory, ReportComment, ReportReview, ReportStatus
from app.schemas.report import (
    ReportCommentCreate,
    ReportCreate,
    ReportQuery,
    ReportReviewCreate,
    ReportUpdate,
)


def _geojson_to_wkb(geojson: dict[str, Any] | None) -> WKBElement | None:
    """GeoJSON dict를 WKBElement로 변환합니다."""
    if geojson is None:
        return None
    geom = shape(geojson)
    from geoalchemy2.shape import from_shape

    return from_shape(geom, srid=4326)


class CRUDReportCategory(CRUDBase[ReportCategory]):
    """CRUD operations for ReportCategory model."""

    async def get_by_slug(self, db: AsyncSession, slug: str) -> ReportCategory | None:
        """Get category by slug."""
        result = await db.execute(select(ReportCategory).where(ReportCategory.slug == slug))
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession) -> list[ReportCategory]:
        """Get all categories."""
        result = await db.execute(select(ReportCategory).order_by(ReportCategory.name))
        return list(result.scalars().all())


class CRUDReport(CRUDBase[Report]):
    """CRUD operations for Report model."""

    async def get_multi_with_query(
        self,
        db: AsyncSession,
        *,
        query: ReportQuery,
    ) -> tuple[list[Report], int]:
        """Get reports with filtering, sorting, and pagination."""
        conditions = []

        if query.search:
            search_term = f"%{query.search}%"
            conditions.append(
                or_(
                    Report.title.ilike(search_term),
                    Report.subtitle.ilike(search_term),
                    Report.summary.ilike(search_term),
                )
            )

        if query.neighborhood_id:
            conditions.append(Report.neighborhood_id == query.neighborhood_id)

        if query.category_id:
            conditions.append(Report.category_id == query.category_id)

        if query.status:
            conditions.append(Report.status == query.status.value)

        if query.author_id:
            conditions.append(Report.author_id == query.author_id)

        if query.min_price is not None:
            conditions.append(Report.price >= query.min_price)

        if query.max_price is not None:
            conditions.append(Report.price <= query.max_price)

        where_clause = and_(*conditions) if conditions else True

        # Order by
        order_by = Report.created_at.desc()
        if query.sort_by == "popular":
            order_by = Report.purchase_count.desc()
        elif query.sort_by == "rating":
            order_by = Report.rating.desc()
        elif query.sort_by == "price_low":
            order_by = Report.price.asc()
        elif query.sort_by == "price_high":
            order_by = Report.price.desc()

        # Get reports
        result = await db.execute(
            select(Report)
            .where(where_clause)
            .order_by(order_by)
            .offset(query.offset)
            .limit(query.limit)
        )
        reports = list(result.scalars().all())

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(Report).where(where_clause)
        )
        total = count_result.scalar() or 0

        return reports, total

    async def get_published(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Report], int]:
        """Get published reports."""
        where_clause = Report.status == ReportStatus.PUBLISHED.value

        result = await db.execute(
            select(Report)
            .where(where_clause)
            .order_by(Report.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        reports = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(Report).where(where_clause)
        )
        total = count_result.scalar() or 0

        return reports, total

    async def get_reports_in_bbox(
        self,
        db: AsyncSession,
        *,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        limit: int = 100,
    ) -> list[Report]:
        """Get published reports within a bounding box."""
        result = await db.execute(
            select(Report)
            .where(
                and_(
                    Report.status == ReportStatus.PUBLISHED.value,
                    Report.latitude.is_not(None),
                    Report.longitude.is_not(None),
                    Report.latitude >= min_lat,
                    Report.latitude <= max_lat,
                    Report.longitude >= min_lng,
                    Report.longitude <= max_lng,
                )
            )
            .order_by(Report.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_report(
        self,
        db: AsyncSession,
        *,
        author_id: str,
        obj_in: ReportCreate,
    ) -> Report:
        """Create a new report."""
        db_obj = Report(
            author_id=author_id,
            neighborhood_id=obj_in.neighborhood_id,
            category_id=obj_in.category_id,
            pnu=obj_in.pnu,
            latitude=obj_in.latitude,
            longitude=obj_in.longitude,
            geometry=_geojson_to_wkb(obj_in.geometry),
            title=obj_in.title,
            subtitle=obj_in.subtitle,
            cover_image=obj_in.cover_image,
            summary=obj_in.summary,
            content=obj_in.content,
            price=obj_in.price,
            original_price=obj_in.original_price,
            tags=obj_in.tags,
            meta_description=obj_in.meta_description,
            status=ReportStatus.DRAFT.value,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_report(
        self,
        db: AsyncSession,
        *,
        db_obj: Report,
        obj_in: ReportUpdate,
    ) -> Report:
        """Update a report."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "status" in update_data:
            update_data["status"] = update_data["status"].value
        if "geometry" in update_data:
            update_data["geometry"] = _geojson_to_wkb(update_data["geometry"])
        update_data["last_updated"] = datetime.utcnow()
        return await self.update(db, db_obj=db_obj, obj_in=update_data)

    async def publish(self, db: AsyncSession, *, db_obj: Report) -> Report:
        """Publish a report."""
        db_obj.status = ReportStatus.PUBLISHED.value
        db_obj.published_at = datetime.utcnow()
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def archive(self, db: AsyncSession, *, db_obj: Report) -> Report:
        """Archive a report."""
        db_obj.status = ReportStatus.ARCHIVED.value
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def increment_purchase_count(
        self,
        db: AsyncSession,
        *,
        db_obj: Report,
    ) -> Report:
        """Increment purchase count."""
        db_obj.purchase_count += 1
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_comment_count(
        self,
        db: AsyncSession,
        *,
        report_id: int,
    ) -> None:
        """Update comment count for a report."""
        count_result = await db.execute(
            select(func.count())
            .select_from(ReportComment)
            .where(ReportComment.report_id == report_id)
        )
        count = count_result.scalar() or 0

        await db.execute(
            Report.__table__.update()
            .where(Report.id == report_id)
            .values(comment_count=count)
        )


class CRUDReportComment(CRUDBase[ReportComment]):
    """CRUD operations for ReportComment model."""

    async def get_by_report(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ReportComment]:
        """Get comments for a report."""
        result = await db.execute(
            select(ReportComment)
            .where(ReportComment.report_id == report_id)
            .order_by(ReportComment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_comment(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        user_id: str,
        obj_in: ReportCommentCreate,
    ) -> ReportComment:
        """Create a new comment."""
        db_obj = ReportComment(
            report_id=report_id,
            user_id=user_id,
            parent_id=obj_in.parent_id,
            content=obj_in.content,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_comment(
        self,
        db: AsyncSession,
        *,
        db_obj: ReportComment,
        content: str,
    ) -> ReportComment:
        """Update a comment."""
        db_obj.content = content
        db_obj.is_edited = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


class CRUDReportReview(CRUDBase[ReportReview]):
    """CRUD operations for ReportReview model."""

    async def get_by_report(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ReportReview], int]:
        """Get reviews for a report."""
        where_clause = ReportReview.report_id == report_id

        result = await db.execute(
            select(ReportReview)
            .where(where_clause)
            .order_by(ReportReview.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        reviews = list(result.scalars().all())

        count_result = await db.execute(
            select(func.count()).select_from(ReportReview).where(where_clause)
        )
        total = count_result.scalar() or 0

        return reviews, total

    async def get_user_review(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        user_id: str,
    ) -> ReportReview | None:
        """Get user's review for a report."""
        result = await db.execute(
            select(ReportReview).where(
                and_(
                    ReportReview.report_id == report_id,
                    ReportReview.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_review(
        self,
        db: AsyncSession,
        *,
        report_id: int,
        user_id: str,
        obj_in: ReportReviewCreate,
    ) -> ReportReview:
        """Create a new review."""
        db_obj = ReportReview(
            report_id=report_id,
            user_id=user_id,
            rating=obj_in.rating,
            content=obj_in.content,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


report_category = CRUDReportCategory(ReportCategory)
report = CRUDReport(Report)
report_comment = CRUDReportComment(ReportComment)
report_review = CRUDReportReview(ReportReview)
