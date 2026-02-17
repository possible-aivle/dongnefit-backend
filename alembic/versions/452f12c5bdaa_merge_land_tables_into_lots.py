"""merge land tables into lots

Revision ID: 452f12c5bdaa
Revises: c9e7b1844a50
Create Date: 2026-02-18 02:20:19.048264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '452f12c5bdaa'
down_revision: Union[str, Sequence[str], None] = 'c9e7b1844a50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 7개 토지 테이블 → lots 통합."""
    # ── Step 1: lots 테이블에 새 컬럼 추가 ──
    # flat 컬럼 (11개)
    op.add_column('lots', sa.Column('jimok', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True))
    op.add_column('lots', sa.Column('jimok_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column('lots', sa.Column('area', sa.Float(), nullable=True))
    op.add_column('lots', sa.Column('use_zone', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))
    op.add_column('lots', sa.Column('use_zone_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column('lots', sa.Column('land_use', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True))
    op.add_column('lots', sa.Column('land_use_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column('lots', sa.Column('official_price', sa.BigInteger(), nullable=True))
    op.add_column('lots', sa.Column('ownership', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True))
    op.add_column('lots', sa.Column('ownership_code', sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))
    op.add_column('lots', sa.Column('owner_count', sa.Integer(), nullable=True))
    # JSONB 컬럼 (4개)
    op.add_column('lots', sa.Column('use_plans', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lots', sa.Column('ownerships', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lots', sa.Column('official_prices', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lots', sa.Column('ancillary_lots', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # ── Step 2: 기존 데이터 마이그레이션 (SQL UPDATE FROM) ──
    conn = op.get_bind()

    # 2a. 토지특성 → lots flat 컬럼 (land_area → area)
    conn.execute(sa.text("""
        UPDATE lots SET
            jimok = lc.jimok,
            area = lc.land_area,
            use_zone = lc.use_zone,
            land_use = lc.land_use,
            official_price = lc.official_price
        FROM land_characteristics lc
        WHERE lots.pnu = lc.pnu
    """))

    # 2b. 토지임야 → lots flat 컬럼 (area는 임야 우선, jimok 보완)
    conn.execute(sa.text("""
        UPDATE lots SET
            jimok = COALESCE(lots.jimok, lf.jimok),
            area = COALESCE(lf.area, lots.area),
            ownership = lf.ownership,
            owner_count = lf.owner_count
        FROM land_and_forest_infos lf
        WHERE lots.pnu = lf.pnu
    """))

    # 2c. 토지이용계획 → lots.use_plans JSONB
    conn.execute(sa.text("""
        UPDATE lots SET use_plans = sub.plans
        FROM (
            SELECT pnu, jsonb_agg(jsonb_build_object('use_district_name', use_district_name)) AS plans
            FROM land_use_plans
            GROUP BY pnu
        ) sub
        WHERE lots.pnu = sub.pnu
    """))

    # 2d. 토지소유정보 → lots.ownerships JSONB
    conn.execute(sa.text("""
        UPDATE lots SET ownerships = sub.owns
        FROM (
            SELECT pnu, jsonb_agg(jsonb_build_object(
                'base_year_month', base_year_month,
                'co_owner_seq', co_owner_seq,
                'ownership_type', ownership_type,
                'ownership_change_reason', ownership_change_reason,
                'ownership_change_date', ownership_change_date,
                'owner_count', owner_count
            )) AS owns
            FROM land_ownerships
            GROUP BY pnu
        ) sub
        WHERE lots.pnu = sub.pnu
    """))

    # 2e. 공시지가 → lots.official_prices JSONB
    conn.execute(sa.text("""
        UPDATE lots SET official_prices = sub.prices
        FROM (
            SELECT pnu, jsonb_agg(jsonb_build_object(
                'base_year', base_year,
                'price_per_sqm', price_per_sqm
            )) AS prices
            FROM official_land_prices
            GROUP BY pnu
        ) sub
        WHERE lots.pnu = sub.pnu
    """))

    # 2f. 부속지번 → lots.ancillary_lots JSONB
    conn.execute(sa.text("""
        UPDATE lots SET ancillary_lots = sub.atch
        FROM (
            SELECT pnu, jsonb_agg(jsonb_build_object(
                'mgm_bldrgst_pk', mgm_bldrgst_pk,
                'atch_pnu', atch_pnu,
                'created_date', created_date
            )) AS atch
            FROM building_register_ancillary_lots
            GROUP BY pnu
        ) sub
        WHERE lots.pnu = sub.pnu
    """))

    # ── Step 3: 구 테이블 삭제 ──
    op.drop_index(op.f('ix_land_use_plans_pnu'), table_name='land_use_plans')
    op.drop_table('land_use_plans')
    op.drop_index(op.f('ix_land_ownerships_pnu'), table_name='land_ownerships')
    op.drop_table('land_ownerships')
    op.drop_index(op.f('ix_building_register_ancillary_lots_mgm_bldrgst_pk'), table_name='building_register_ancillary_lots')
    op.drop_index(op.f('ix_building_register_ancillary_lots_pnu'), table_name='building_register_ancillary_lots')
    op.drop_table('building_register_ancillary_lots')
    op.drop_index(op.f('ix_official_land_prices_pnu'), table_name='official_land_prices')
    op.drop_table('official_land_prices')
    op.drop_index(op.f('ix_land_and_forest_infos_pnu'), table_name='land_and_forest_infos')
    op.drop_table('land_and_forest_infos')
    op.drop_index(op.f('ix_land_characteristics_pnu'), table_name='land_characteristics')
    op.drop_table('land_characteristics')


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lots', 'ancillary_lots')
    op.drop_column('lots', 'official_prices')
    op.drop_column('lots', 'ownerships')
    op.drop_column('lots', 'use_plans')
    op.drop_column('lots', 'owner_count')
    op.drop_column('lots', 'ownership_code')
    op.drop_column('lots', 'ownership')
    op.drop_column('lots', 'official_price')
    op.drop_column('lots', 'land_use_code')
    op.drop_column('lots', 'land_use')
    op.drop_column('lots', 'use_zone_code')
    op.drop_column('lots', 'use_zone')
    op.drop_column('lots', 'area')
    op.drop_column('lots', 'jimok_code')
    op.drop_column('lots', 'jimok')
    op.create_table('land_characteristics',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('jimok', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('land_area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('use_zone', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('land_use', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('official_price', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('land_characteristics_pkey')),
    sa.UniqueConstraint('pnu', name=op.f('uq_land_char_pnu'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_land_characteristics_pnu'), 'land_characteristics', ['pnu'], unique=False)
    op.create_table('land_and_forest_infos',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('jimok', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('area', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('ownership', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('owner_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('land_and_forest_infos_pkey')),
    sa.UniqueConstraint('pnu', name=op.f('uq_land_forest_pnu'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_land_and_forest_infos_pnu'), 'land_and_forest_infos', ['pnu'], unique=False)
    op.create_table('official_land_prices',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('base_year', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('price_per_sqm', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('official_land_prices_pkey')),
    sa.UniqueConstraint('pnu', 'base_year', name=op.f('uq_official_price_pnu_year'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_official_land_prices_pnu'), 'official_land_prices', ['pnu'], unique=False)
    op.create_table('building_register_ancillary_lots',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('mgm_bldrgst_pk', sa.VARCHAR(length=33), autoincrement=False, nullable=False),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('atch_pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=True),
    sa.Column('created_date', sa.VARCHAR(length=8), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('building_register_ancillary_lots_pkey')),
    sa.UniqueConstraint('mgm_bldrgst_pk', 'atch_pnu', name=op.f('uq_bldrgst_ancillary_lot'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_building_register_ancillary_lots_pnu'), 'building_register_ancillary_lots', ['pnu'], unique=False)
    op.create_index(op.f('ix_building_register_ancillary_lots_mgm_bldrgst_pk'), 'building_register_ancillary_lots', ['mgm_bldrgst_pk'], unique=False)
    op.create_table('land_ownerships',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('base_year_month', sa.VARCHAR(length=7), autoincrement=False, nullable=False),
    sa.Column('co_owner_seq', sa.VARCHAR(length=6), autoincrement=False, nullable=False),
    sa.Column('ownership_type', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('ownership_change_reason', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
    sa.Column('ownership_change_date', sa.VARCHAR(length=10), autoincrement=False, nullable=True),
    sa.Column('owner_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('land_ownerships_pkey')),
    sa.UniqueConstraint('pnu', 'co_owner_seq', name=op.f('uq_land_ownership_pnu_seq'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_land_ownerships_pnu'), 'land_ownerships', ['pnu'], unique=False)
    op.create_table('land_use_plans',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('pnu', sa.VARCHAR(length=19), autoincrement=False, nullable=False),
    sa.Column('use_district_name', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('land_use_plans_pkey')),
    sa.UniqueConstraint('pnu', 'use_district_name', name=op.f('uq_land_use_pnu_name'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_land_use_plans_pnu'), 'land_use_plans', ['pnu'], unique=False)
    # ### end Alembic commands ###
