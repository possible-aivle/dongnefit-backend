"""Property model for real estate data."""

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class Property(Base, TimestampMixin):
    """Real estate property model."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    road_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Coordinates
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Property details
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    area: Mapped[float | None] = mapped_column(Float, nullable=True)  # in square meters
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additional data
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
