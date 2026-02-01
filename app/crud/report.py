"""CRUD operations for reports."""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.report import Report, ReportCategory, ReportReview, ReportStatus
from app.schemas.report import ReportCreate, ReportQuery, ReportReviewCreate, ReportUpdate


class CRUDReportCategory(CRUDBase[ReportCategory]):
    """CRUD operations for ReportCategory model."""

    async def get_by_slug(self, db: AsyncSession, slug: str) -> ReportCategory | None:
        """Get category by slug."""
        result = await db.execute(
            select(ReportCategory).where(ReportCategory.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession) -> list[ReportCategory]:
        """Get all categories."""
        result = await db.execute(
            select(ReportCategory).order_by(ReportCategory.name)
        )
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
report_review = CRUDReportReview(ReportReview)
