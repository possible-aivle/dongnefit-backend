"""add sgg_code and bigint amounts

Revision ID: 675a0788be23
Revises: 5ac682a04de1
Create Date: 2026-02-17 17:11:46.956690

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '675a0788be23'
down_revision: str | Sequence[str] | None = '5ac682a04de1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """sgg_code 컬럼 추가, 금액 컬럼 INTEGER -> BIGINT 변환."""
    # ── real_estate_sales ──
    op.add_column('real_estate_sales', sa.Column(
        'sgg_code', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True,
    ))
    op.create_index('ix_real_estate_sales_sgg_code', 'real_estate_sales', ['sgg_code'])
    op.alter_column(
        'real_estate_sales', 'transaction_amount',
        type_=sa.BigInteger(),
        existing_type=sa.Integer(),
        existing_nullable=True,
    )

    # ── real_estate_rentals ──
    op.add_column('real_estate_rentals', sa.Column(
        'sgg_code', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True,
    ))
    op.create_index('ix_real_estate_rentals_sgg_code', 'real_estate_rentals', ['sgg_code'])
    op.alter_column(
        'real_estate_rentals', 'deposit',
        type_=sa.BigInteger(),
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        'real_estate_rentals', 'monthly_rent_amount',
        type_=sa.BigInteger(),
        existing_type=sa.Integer(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert: sgg_code 제거, BIGINT -> INTEGER."""
    # ── real_estate_rentals ──
    op.alter_column(
        'real_estate_rentals', 'monthly_rent_amount',
        type_=sa.Integer(),
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        'real_estate_rentals', 'deposit',
        type_=sa.Integer(),
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
    op.drop_index('ix_real_estate_rentals_sgg_code', table_name='real_estate_rentals')
    op.drop_column('real_estate_rentals', 'sgg_code')

    # ── real_estate_sales ──
    op.alter_column(
        'real_estate_sales', 'transaction_amount',
        type_=sa.Integer(),
        existing_type=sa.BigInteger(),
        existing_nullable=True,
    )
    op.drop_index('ix_real_estate_sales_sgg_code', table_name='real_estate_sales')
    op.drop_column('real_estate_sales', 'sgg_code')
