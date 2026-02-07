"""CRUD operations for neighborhoods."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, func, or_, select

from app.crud.base import CRUDBase
from app.models.neighborhood import Neighborhood
from app.schemas.neighborhood import NeighborhoodCreate, NeighborhoodQuery, NeighborhoodUpdate


class CRUDNeighborhood(CRUDBase[Neighborhood]):
    """CRUD operations for Neighborhood model."""

    async def get_multi_with_query(
        self,
        db: AsyncSession,
        *,
        query: NeighborhoodQuery,
    ) -> tuple[list[Neighborhood], int]:
        """Get neighborhoods with filtering and pagination."""
        conditions = []

        if query.search:
            search_term = f"%{query.search}%"
            conditions.append(
                or_(
                    Neighborhood.name.ilike(search_term),
                    Neighborhood.district.ilike(search_term),
                    Neighborhood.city.ilike(search_term),
                )
            )

        if query.city:
            conditions.append(Neighborhood.city == query.city)

        if query.district:
            conditions.append(Neighborhood.district == query.district)

        where_clause = and_(*conditions) if conditions else True

        # Order by
        order_by = Neighborhood.name.asc()
        if query.sort_by == "newest":
            order_by = Neighborhood.created_at.desc()

        # Get neighborhoods
        result = await db.execute(
            select(Neighborhood)
            .where(where_clause)
            .order_by(order_by)
            .offset(query.offset)
            .limit(query.limit)
        )
        neighborhoods = list(result.scalars().all())

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(Neighborhood).where(where_clause)
        )
        total = count_result.scalar() or 0

        return neighborhoods, total

    async def create_neighborhood(
        self,
        db: AsyncSession,
        *,
        obj_in: NeighborhoodCreate,
    ) -> Neighborhood:
        """Create a new neighborhood."""
        db_obj = Neighborhood(
            name=obj_in.name,
            district=obj_in.district,
            city=obj_in.city,
            coordinates=obj_in.coordinates.model_dump() if obj_in.coordinates else None,
            description=obj_in.description,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_neighborhood(
        self,
        db: AsyncSession,
        *,
        db_obj: Neighborhood,
        obj_in: NeighborhoodUpdate,
    ) -> Neighborhood:
        """Update a neighborhood."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "coordinates" in update_data and update_data["coordinates"]:
            update_data["coordinates"] = update_data["coordinates"].model_dump()
        return await self.update(db, db_obj=db_obj, obj_in=update_data)

    async def search_by_location(
        self,
        db: AsyncSession,
        *,
        lat: float,
        lng: float,
        radius_km: float = 5.0,
    ) -> list[Neighborhood]:
        """Find neighborhoods near a location."""
        # PostgreSQL Earth distance calculation
        # This is a simplified version - for production, use PostGIS
        result = await db.execute(
            select(Neighborhood).where(Neighborhood.coordinates.isnot(None)).limit(20)
        )
        neighborhoods = list(result.scalars().all())

        # Filter by distance (simplified Haversine approximation)
        nearby = []
        for n in neighborhoods:
            if n.coordinates:
                n_lat = n.coordinates.get("lat", 0)
                n_lng = n.coordinates.get("lng", 0)
                # Simple distance check (not accurate for large distances)
                lat_diff = abs(n_lat - lat) * 111  # ~111km per degree
                lng_diff = abs(n_lng - lng) * 88.8  # ~88.8km per degree at ~37°N
                distance = (lat_diff**2 + lng_diff**2) ** 0.5
                if distance <= radius_km:
                    nearby.append(n)

        return nearby

    async def get_cities(self, db: AsyncSession) -> list[str]:
        """Get list of unique cities."""
        result = await db.execute(select(Neighborhood.city).distinct().order_by(Neighborhood.city))
        return [row[0] for row in result.all()]

    async def get_districts(self, db: AsyncSession, city: str) -> list[str]:
        """Get list of districts in a city."""
        result = await db.execute(
            select(Neighborhood.district)
            .where(Neighborhood.city == city)
            .distinct()
            .order_by(Neighborhood.district)
        )
        return [row[0] for row in result.all()]


neighborhood = CRUDNeighborhood(Neighborhood)
