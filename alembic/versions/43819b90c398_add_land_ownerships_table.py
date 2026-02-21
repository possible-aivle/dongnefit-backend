"""add_land_ownerships_table

Revision ID: 43819b90c398
Revises: 43ee1074f345
Create Date: 2026-02-16 13:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '43819b90c398'
down_revision: str | Sequence[str] | None = '43ee1074f345'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'land_ownerships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pnu', sa.String(length=19), nullable=False),
        sa.Column('base_year_month', sa.String(length=7), nullable=False),
        sa.Column('co_owner_seq', sa.String(length=6), nullable=False),
        sa.Column('ownership_type', sa.String(length=20), nullable=True),
        sa.Column('ownership_change_reason', sa.String(length=30), nullable=True),
        sa.Column('ownership_change_date', sa.String(length=10), nullable=True),
        sa.Column('owner_count', sa.Integer(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['pnu'], ['lots.pnu']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pnu', 'co_owner_seq', name='uq_land_ownership_pnu_seq'),
    )
    op.create_index(op.f('ix_land_ownerships_pnu'), 'land_ownerships', ['pnu'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_land_ownerships_pnu'), table_name='land_ownerships')
    op.drop_table('land_ownerships')
