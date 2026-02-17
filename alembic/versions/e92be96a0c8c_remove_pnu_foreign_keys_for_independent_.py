"""remove pnu foreign keys for independent pipeline loading

Revision ID: e92be96a0c8c
Revises: 1a02c61ab5a0
Create Date: 2026-02-16 15:38:13.710313

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e92be96a0c8c'
down_revision: str | Sequence[str] | None = '1a02c61ab5a0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """PNU FK 제약 제거 - 파이프라인 독립 적재 지원."""
    op.drop_constraint('ancillary_lands_pnu_fkey', 'ancillary_lands', type_='foreignkey')
    op.drop_constraint('building_register_ancillary_lots_pnu_fkey', 'building_register_ancillary_lots', type_='foreignkey')
    op.drop_constraint('building_register_areas_pnu_fkey', 'building_register_areas', type_='foreignkey')
    op.drop_constraint('building_register_floor_details_pnu_fkey', 'building_register_floor_details', type_='foreignkey')
    op.drop_constraint('building_register_generals_pnu_fkey', 'building_register_generals', type_='foreignkey')
    op.drop_constraint('building_register_headers_pnu_fkey', 'building_register_headers', type_='foreignkey')
    op.drop_constraint('gis_building_integrated_pnu_fkey', 'gis_building_integrated', type_='foreignkey')
    op.drop_constraint('land_and_forest_infos_pnu_fkey', 'land_and_forest_infos', type_='foreignkey')
    op.drop_constraint('land_characteristics_pnu_fkey', 'land_characteristics', type_='foreignkey')
    op.drop_constraint('land_ownerships_pnu_fkey', 'land_ownerships', type_='foreignkey')
    op.drop_constraint('land_use_plans_pnu_fkey', 'land_use_plans', type_='foreignkey')
    op.drop_constraint('official_land_prices_pnu_fkey', 'official_land_prices', type_='foreignkey')


def downgrade() -> None:
    """PNU FK 제약 복원."""
    op.create_foreign_key('official_land_prices_pnu_fkey', 'official_land_prices', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('land_use_plans_pnu_fkey', 'land_use_plans', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('land_ownerships_pnu_fkey', 'land_ownerships', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('land_characteristics_pnu_fkey', 'land_characteristics', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('land_and_forest_infos_pnu_fkey', 'land_and_forest_infos', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('gis_building_integrated_pnu_fkey', 'gis_building_integrated', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('building_register_headers_pnu_fkey', 'building_register_headers', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('building_register_generals_pnu_fkey', 'building_register_generals', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('building_register_floor_details_pnu_fkey', 'building_register_floor_details', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('building_register_areas_pnu_fkey', 'building_register_areas', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('building_register_ancillary_lots_pnu_fkey', 'building_register_ancillary_lots', 'lots', ['pnu'], ['pnu'])
    op.create_foreign_key('ancillary_lands_pnu_fkey', 'ancillary_lands', 'lots', ['pnu'], ['pnu'])
