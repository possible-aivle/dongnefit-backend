"""Base schemas and utilities."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination query parameters."""

    page: int = 1
    limit: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseSchema):
    """Pagination metadata in response."""

    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseSchema):
    """Generic paginated response."""

    data: list[T]
    pagination: PaginationMeta
