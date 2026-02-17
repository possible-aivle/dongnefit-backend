"""add address and drop sigungu from real_estate_sales and real_estate_rentals

Revision ID: 5ac682a04de1
Revises: 922ba75f4289
Create Date: 2026-02-17 15:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ac682a04de1"
down_revision: str | None = "922ba75f4289"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── real_estate_sales ──
    op.add_column(
        "real_estate_sales",
        sa.Column("address", sa.String(length=200), nullable=True),
    )
    op.create_index(
        op.f("ix_real_estate_sales_address"),
        "real_estate_sales",
        ["address"],
    )
    op.drop_index("ix_real_estate_sales_sigungu", table_name="real_estate_sales")
    op.drop_column("real_estate_sales", "sigungu")

    # ── real_estate_rentals ──
    op.add_column(
        "real_estate_rentals",
        sa.Column("address", sa.String(length=200), nullable=True),
    )
    op.create_index(
        op.f("ix_real_estate_rentals_address"),
        "real_estate_rentals",
        ["address"],
    )
    op.drop_index("ix_real_estate_rentals_sigungu", table_name="real_estate_rentals")
    op.drop_column("real_estate_rentals", "sigungu")


def downgrade() -> None:
    # ── real_estate_rentals ──
    op.add_column(
        "real_estate_rentals",
        sa.Column("sigungu", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_real_estate_rentals_sigungu",
        "real_estate_rentals",
        ["sigungu"],
    )
    op.drop_index(
        op.f("ix_real_estate_rentals_address"),
        table_name="real_estate_rentals",
    )
    op.drop_column("real_estate_rentals", "address")

    # ── real_estate_sales ──
    op.add_column(
        "real_estate_sales",
        sa.Column("sigungu", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_real_estate_sales_sigungu",
        "real_estate_sales",
        ["sigungu"],
    )
    op.drop_index(
        op.f("ix_real_estate_sales_address"),
        table_name="real_estate_sales",
    )
    op.drop_column("real_estate_sales", "address")
