"""drop unused columns pnu contract_area land_category use_area admin_code sido_code sgg_code emd_code

Revision ID: 922ba75f4289
Revises: a84d805dc798
Create Date: 2026-02-17 02:57:44.198701

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '922ba75f4289'
down_revision: str | Sequence[str] | None = 'a84d805dc798'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """불필요한 컬럼 제거 (100% NULL 또는 PNU 파생 중복)."""
    # real_estate_sales: 100% NULL 컬럼 4개
    op.drop_column("real_estate_sales", "pnu")
    op.drop_column("real_estate_sales", "contract_area")
    op.drop_column("real_estate_sales", "land_category")
    op.drop_column("real_estate_sales", "use_area")

    # real_estate_rentals: pnu도 100% NULL
    op.drop_column("real_estate_rentals", "pnu")

    # road_center_lines: admin_code 100% NULL
    op.drop_column("road_center_lines", "admin_code")

    # lots: PNU에서 파생 가능한 중복 컬럼 3개
    op.drop_column("lots", "sido_code")
    op.drop_column("lots", "sgg_code")
    op.drop_column("lots", "emd_code")


def downgrade() -> None:
    """제거된 컬럼 복원 (데이터는 복구 불가)."""
    # lots
    op.add_column("lots", sa.Column("emd_code", sa.VARCHAR(length=8), nullable=False, server_default=""))
    op.add_column("lots", sa.Column("sgg_code", sa.VARCHAR(length=5), nullable=False, server_default=""))
    op.add_column("lots", sa.Column("sido_code", sa.VARCHAR(length=2), nullable=False, server_default=""))
    op.create_index("ix_lots_sido_code", "lots", ["sido_code"])
    op.create_index("ix_lots_sgg_code", "lots", ["sgg_code"])
    op.create_index("ix_lots_emd_code", "lots", ["emd_code"])

    # road_center_lines
    op.add_column("road_center_lines", sa.Column("admin_code", sa.VARCHAR(length=10), nullable=True))
    op.create_index("ix_road_center_lines_admin_code", "road_center_lines", ["admin_code"])

    # real_estate_rentals
    op.add_column("real_estate_rentals", sa.Column("pnu", sa.VARCHAR(length=19), nullable=True))
    op.create_index("ix_real_estate_rentals_pnu", "real_estate_rentals", ["pnu"])

    # real_estate_sales
    op.add_column("real_estate_sales", sa.Column("use_area", sa.VARCHAR(length=50), nullable=True))
    op.add_column("real_estate_sales", sa.Column("land_category", sa.VARCHAR(length=20), nullable=True))
    op.add_column("real_estate_sales", sa.Column("contract_area", sa.DOUBLE_PRECISION(), nullable=True))
    op.add_column("real_estate_sales", sa.Column("pnu", sa.VARCHAR(length=19), nullable=True))
    op.create_index("ix_real_estate_sales_pnu", "real_estate_sales", ["pnu"])
