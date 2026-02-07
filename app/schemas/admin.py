"""Admin schemas."""

from app.schemas.base import BaseSchema

# === Analytics Schemas ===


class AnalyticsSummary(BaseSchema):
    """Analytics summary."""

    total_users: int
    active_users: int
    total_reports: int
    published_reports: int
    total_discussions: int
    total_orders: int
    total_revenue: int


class UserAnalytics(BaseSchema):
    """User analytics."""

    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    active_users_today: int


class NeighborhoodAnalytics(BaseSchema):
    """Neighborhood analytics."""

    neighborhood_id: int
    name: str
    member_count: int
    report_count: int
    discussion_count: int
    engagement_score: float
