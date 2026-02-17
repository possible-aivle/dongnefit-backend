"""remove updated_at from public data tables

Revision ID: a84d805dc798
Revises: 0d79360abab7
Create Date: 2026-02-17 02:08:11.778387

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a84d805dc798'
down_revision: str | Sequence[str] | None = '0d79360abab7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 공공데이터 테이블 목록
PUBLIC_DATA_TABLES = [
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
    """공공데이터 테이블에서 updated_at 컬럼 제거."""
    for table in PUBLIC_DATA_TABLES:
        op.drop_column(table, "updated_at")


def downgrade() -> None:
    """공공데이터 테이블에 updated_at 컬럼 복원."""
    for table in PUBLIC_DATA_TABLES:
        op.add_column(
            table,
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
