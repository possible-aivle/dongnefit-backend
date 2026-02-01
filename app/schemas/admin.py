"""Admin schemas."""

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.base import PaginationParams, TimestampSchema
from app.schemas.user import UserPublic


class ViolationStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# === Admin Activity Schemas ===


class AdminActivityQuery(PaginationParams):
    """Query parameters for admin activities."""

    admin_id: str | None = None
    action: str | None = None
    target_type: str | None = None


class AdminActivityResponse(TimestampSchema):
    """Admin activity response."""

    id: int
    admin_id: str
    action: str
    target_type: str | None
    target_id: str | None
    description: str | None
    metadata: dict | None
    ip_address: str | None
    admin: UserPublic | None = None


# === Violation Complaint Schemas ===


class ViolationComplaintCreate(BaseModel):
    """Schema for creating a violation complaint."""

    target_type: str  # 'discussion', 'reply', 'user'
    target_id: int
    reason: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ViolationComplaintResolve(BaseModel):
    """Schema for resolving a violation complaint."""

    status: ViolationStatus
    resolution_note: str | None = None


class ViolationComplaintQuery(PaginationParams):
    """Query parameters for violation complaints."""

    status: ViolationStatus | None = None
    target_type: str | None = None
    reporter_id: str | None = None


class ViolationComplaintResponse(TimestampSchema):
    """Violation complaint response."""

    id: int
    reporter_id: str
    target_type: str
    target_id: int
    reason: str
    description: str | None
    status: ViolationStatus
    resolved_by: str | None
    resolution_note: str | None
    reporter: UserPublic | None = None


# === Analytics Schemas ===


class AnalyticsSummary(BaseModel):
    """Analytics summary."""

    total_users: int
    active_users: int
    total_reports: int
    published_reports: int
    total_discussions: int
    total_orders: int
    total_revenue: int


class UserAnalytics(BaseModel):
    """User analytics."""

    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    active_users_today: int


class NeighborhoodAnalytics(BaseModel):
    """Neighborhood analytics."""

    neighborhood_id: int
    name: str
    member_count: int
    report_count: int
    discussion_count: int
    engagement_score: float
