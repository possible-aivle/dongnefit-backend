"""Neighborhood model for location-based services."""

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Neighborhood(Base, TimestampMixin):
    """Neighborhood/district model."""

    __tablename__ = "neighborhoods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)  # 구/군
    city: Mapped[str] = mapped_column(String(100), nullable=False)  # 시/도
    coordinates: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {lat, lng}
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
