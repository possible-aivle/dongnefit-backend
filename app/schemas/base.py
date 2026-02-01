"""Base schemas and utilities."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""

    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseModel):
    """Generic paginated response."""

    data: list[T]
    pagination: PaginationMeta
