"""remove raw_data and simplify geometry

Revision ID: 0d79360abab7
Revises: 39ed7534c022
Create Date: 2026-02-17 01:55:03.447407

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0d79360abab7'
down_revision: str | Sequence[str] | None = '39ed7534c022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# raw_data 컬럼을 제거할 테이블 목록 (18개)
RAW_DATA_TABLES = [
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
    "official_land_prices",
    "real_estate_rentals",
    "real_estate_sales",
    "road_center_lines",
    "use_region_districts",
]

# geometry 단순화 대상 테이블 (행정경계 + 용도지역지구)
SIMPLIFY_TABLES = [
    "administrative_divisions",
    "administrative_emds",
    "use_region_districts",
]

SIMPLIFY_TOLERANCE = 0.001  # ~111m 해상도


def upgrade() -> None:
    """raw_data 컬럼 제거 + geometry 단순화."""
    # 1) raw_data 컬럼 제거
    for table in RAW_DATA_TABLES:
        op.drop_column(table, "raw_data")

    # 2) 기존 geometry 데이터 단순화 (ST_Simplify)
    for table in SIMPLIFY_TABLES:
        op.execute(
            sa.text(
                f"UPDATE {table} SET geometry = ST_Simplify(geometry, {SIMPLIFY_TOLERANCE}) "
                f"WHERE geometry IS NOT NULL"
            )
        )


def downgrade() -> None:
    """raw_data 컬럼 복원 (데이터는 복구 불가)."""
    for table in reversed(RAW_DATA_TABLES):
        op.add_column(
            table,
            sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    # geometry 단순화는 비가역적 — 원본 복구 불가
