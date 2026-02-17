"""drop_individual_house_prices_and_apartment_prices_tables

Revision ID: 43ee1074f345
Revises: 253bae5c3109
Create Date: 2026-02-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '43ee1074f345'
down_revision: Union[str, Sequence[str], None] = '253bae5c3109'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f('ix_individual_house_prices_pnu'), table_name='individual_house_prices')
    op.drop_table('individual_house_prices')

    op.drop_index(op.f('ix_apartment_prices_pnu'), table_name='apartment_prices')
    op.drop_table('apartment_prices')


def downgrade() -> None:
    op.create_table(
        'individual_house_prices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pnu', sa.String(length=19), nullable=False),
        sa.Column('base_year', sa.Integer(), nullable=False),
        sa.Column('house_price', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pnu'], ['lots.pnu']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pnu', 'base_year', name='uq_ind_house_pnu_year'),
    )
    op.create_index(op.f('ix_individual_house_prices_pnu'), 'individual_house_prices', ['pnu'], unique=False)

    op.create_table(
        'apartment_prices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pnu', sa.String(length=19), nullable=False),
        sa.Column('base_year', sa.Integer(), nullable=False),
        sa.Column('apt_type_name', sa.String(length=20), nullable=True),
        sa.Column('apt_name', sa.String(length=100), nullable=True),
        sa.Column('dong_name', sa.String(length=50), nullable=True),
        sa.Column('ho_name', sa.String(length=10), nullable=True),
        sa.Column('exclusive_area', sa.Float(), nullable=True),
        sa.Column('official_price', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pnu'], ['lots.pnu']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pnu', 'base_year', 'dong_name', 'ho_name', name='uq_apt_price'),
    )
    op.create_index(op.f('ix_apartment_prices_pnu'), 'apartment_prices', ['pnu'], unique=False)
