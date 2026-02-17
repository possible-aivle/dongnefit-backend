"""drop jibun_address data_year rename land fields

Revision ID: b87c43462b62
Revises: 4e696ca65b61
Create Date: 2026-02-18 01:31:34.524795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b87c43462b62'
down_revision: Union[str, Sequence[str], None] = '4e696ca65b61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # -- lots: drop jibun_address --
    op.drop_column('lots', 'jibun_address')

    # -- land_characteristics: rename fields, drop data_year --
    op.alter_column('land_characteristics', 'jimok_name', new_column_name='jimok')
    op.alter_column('land_characteristics', 'use_zone_name', new_column_name='use_zone')
    op.alter_column('land_characteristics', 'land_use_name', new_column_name='land_use')
    op.drop_constraint('uq_land_char_pnu_year', 'land_characteristics', type_='unique')
    op.drop_column('land_characteristics', 'data_year')
    op.create_unique_constraint('uq_land_char_pnu', 'land_characteristics', ['pnu'])

    # -- land_use_plans: drop data_year --
    op.drop_constraint('uq_land_use_pnu_year_name', 'land_use_plans', type_='unique')
    op.drop_column('land_use_plans', 'data_year')
    op.create_unique_constraint('uq_land_use_pnu_name', 'land_use_plans', ['pnu', 'use_district_name'])

    # -- land_and_forest_infos: rename fields, drop data_year --
    op.alter_column('land_and_forest_infos', 'jimok_name', new_column_name='jimok')
    op.alter_column('land_and_forest_infos', 'ownership_name', new_column_name='ownership')
    op.drop_constraint('uq_land_forest_pnu_year', 'land_and_forest_infos', type_='unique')
    op.drop_column('land_and_forest_infos', 'data_year')
    op.create_unique_constraint('uq_land_forest_pnu', 'land_and_forest_infos', ['pnu'])


def downgrade() -> None:
    """Downgrade schema."""
    # -- lots: restore jibun_address --
    op.add_column('lots', sa.Column('jibun_address', sa.VARCHAR(length=500), nullable=True))

    # -- land_characteristics: restore fields --
    op.drop_constraint('uq_land_char_pnu', 'land_characteristics', type_='unique')
    op.add_column('land_characteristics', sa.Column('data_year', sa.INTEGER(), nullable=False, server_default='0'))
    op.alter_column('land_characteristics', 'jimok', new_column_name='jimok_name')
    op.alter_column('land_characteristics', 'use_zone', new_column_name='use_zone_name')
    op.alter_column('land_characteristics', 'land_use', new_column_name='land_use_name')
    op.create_unique_constraint('uq_land_char_pnu_year', 'land_characteristics', ['pnu', 'data_year'])

    # -- land_use_plans: restore data_year --
    op.drop_constraint('uq_land_use_pnu_name', 'land_use_plans', type_='unique')
    op.add_column('land_use_plans', sa.Column('data_year', sa.INTEGER(), nullable=False, server_default='0'))
    op.create_unique_constraint('uq_land_use_pnu_year_name', 'land_use_plans', ['pnu', 'data_year', 'use_district_name'])

    # -- land_and_forest_infos: restore fields --
    op.drop_constraint('uq_land_forest_pnu', 'land_and_forest_infos', type_='unique')
    op.add_column('land_and_forest_infos', sa.Column('data_year', sa.INTEGER(), nullable=False, server_default='0'))
    op.alter_column('land_and_forest_infos', 'jimok', new_column_name='jimok_name')
    op.alter_column('land_and_forest_infos', 'ownership', new_column_name='ownership_name')
    op.create_unique_constraint('uq_land_forest_pnu_year', 'land_and_forest_infos', ['pnu', 'data_year'])
