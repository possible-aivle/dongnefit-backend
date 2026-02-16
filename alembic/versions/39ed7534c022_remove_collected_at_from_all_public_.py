"""remove collected_at from all public data tables

Revision ID: 39ed7534c022
Revises: e92be96a0c8c
Create Date: 2026-02-17 01:19:16.846273

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '39ed7534c022'
down_revision: Union[str, Sequence[str], None] = 'e92be96a0c8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# collected_at 컬럼을 제거할 테이블 목록
TABLES = [
    "administrative_divisions",
    "administrative_emds",
    "ancillary_lands",
    "building_register_ancillary_lots",
    "building_register_areas",
    "building_register_floor_details",
    "building_register_generals",
    "building_register_headers",
    "gis_building_integrated",
    "land_and_forest_infos",
    "land_characteristics",
    "land_ownerships",
    "land_use_plans",
    "lots",
    "official_land_prices",
    "real_estate_rentals",
    "real_estate_sales",
    "road_center_lines",
    "use_region_districts",
]


def upgrade() -> None:
    """Drop collected_at column from all public data tables."""
    for table in TABLES:
        op.drop_column(table, "collected_at")


def downgrade() -> None:
    """Re-add collected_at column to all public data tables."""
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "collected_at",
                postgresql.TIMESTAMP(),
                autoincrement=False,
                nullable=True,
            ),
        )
