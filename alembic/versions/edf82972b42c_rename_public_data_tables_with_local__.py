"""rename public data tables with local_ prefix

Revision ID: edf82972b42c
Revises: 3dde80897250
Create Date: 2026-02-22 13:54:34.520213

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'edf82972b42c'
down_revision: Union[str, Sequence[str], None] = '3dde80897250'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (old_table, new_table)
_TABLE_RENAMES = [
    ("lots", "local_lots"),
    ("building_register_headers", "local_building_register_headers"),
    ("building_register_generals", "local_building_register_generals"),
    ("building_register_floor_details", "local_building_register_floor_details"),
    ("building_register_areas", "local_building_register_areas"),
    ("gis_building_integrated", "local_gis_building_integrated"),
    ("real_estate_sales", "local_real_estate_sales"),
    ("real_estate_rentals", "local_real_estate_rentals"),
    ("administrative_sidos", "local_administrative_sidos"),
    ("administrative_sggs", "local_administrative_sggs"),
    ("administrative_emds", "local_administrative_emds"),
    ("road_center_lines", "local_road_center_lines"),
    ("use_region_districts", "local_use_region_districts"),
]

# (old_index, new_index) — auto-generated indexes whose names include table name
_INDEX_RENAMES = [
    # lots
    ("idx_lots_geometry", "idx_local_lots_geometry"),
    # building_register_headers
    ("ix_building_register_headers_pnu", "ix_local_building_register_headers_pnu"),
    # building_register_generals
    ("ix_building_register_generals_pnu", "ix_local_building_register_generals_pnu"),
    # building_register_floor_details
    ("ix_building_register_floor_details_mgm_bldrgst_pk", "ix_local_building_register_floor_details_mgm_bldrgst_pk"),
    ("ix_building_register_floor_details_pnu", "ix_local_building_register_floor_details_pnu"),
    # building_register_areas
    ("ix_building_register_areas_mgm_bldrgst_pk", "ix_local_building_register_areas_mgm_bldrgst_pk"),
    ("ix_building_register_areas_pnu", "ix_local_building_register_areas_pnu"),
    # gis_building_integrated
    ("idx_gis_building_integrated_geometry", "idx_local_gis_building_integrated_geometry"),
    ("ix_gis_building_integrated_pnu", "ix_local_gis_building_integrated_pnu"),
    # real_estate_sales
    ("ix_real_estate_sales_address", "ix_local_real_estate_sales_address"),
    # real_estate_rentals
    ("ix_real_estate_rentals_address", "ix_local_real_estate_rentals_address"),
    # administrative_sidos
    ("idx_administrative_sidos_geometry", "idx_local_administrative_sidos_geometry"),
    # administrative_sggs
    ("idx_administrative_sggs_geometry", "idx_local_administrative_sggs_geometry"),
    ("ix_administrative_sggs_sido_code", "ix_local_administrative_sggs_sido_code"),
    # administrative_emds
    ("idx_administrative_emds_geometry", "idx_local_administrative_emds_geometry"),
    ("ix_administrative_emds_sgg_code", "ix_local_administrative_emds_sgg_code"),
    # road_center_lines
    ("idx_road_center_lines_geometry", "idx_local_road_center_lines_geometry"),
    # use_region_districts
    ("idx_use_region_districts_geometry", "idx_local_use_region_districts_geometry"),
    ("ix_use_region_districts_admin_code", "ix_local_use_region_districts_admin_code"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for old_name, new_name in _TABLE_RENAMES:
        op.rename_table(old_name, new_name)

    for old_idx, new_idx in _INDEX_RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{old_idx}" RENAME TO "{new_idx}"')


def downgrade() -> None:
    """Downgrade schema."""
    for old_name, new_name in _TABLE_RENAMES:
        op.rename_table(new_name, old_name)

    for old_idx, new_idx in _INDEX_RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{new_idx}" RENAME TO "{old_idx}"')
