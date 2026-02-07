"""Neighborhood model for location-based services."""

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import TimestampMixin


class Neighborhood(TimestampMixin, table=True):
    """Neighborhood/district model."""

    __tablename__ = "neighborhoods"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    district: str = Field(max_length=100)  # 구/군
    city: str = Field(max_length=100)  # 시/도
    coordinates: dict | None = Field(default=None, sa_column=Column(JSON))  # {lat, lng}
    description: str | None = Field(default=None)
