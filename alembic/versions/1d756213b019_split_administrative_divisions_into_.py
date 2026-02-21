"""split_administrative_divisions_into_sido_and_sgg

Revision ID: 1d756213b019
Revises: 62c51e1157ae
Create Date: 2026-02-17 21:17:34.953223

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
import sqlmodel
from geoalchemy2 import Geometry

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1d756213b019'
down_revision: str | Sequence[str] | None = '62c51e1157ae'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Split administrative_divisions into administrative_sidos and administrative_sggs."""
    # 1. 새 테이블 생성: administrative_sidos (시도)
    op.create_geospatial_table('administrative_sidos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sido_code', sqlmodel.sql.sqltypes.AutoString(length=2), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('geometry', Geometry(srid=4326, dimension=2, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_geospatial_index('idx_administrative_sidos_geometry', 'administrative_sidos', ['geometry'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_administrative_sidos_sido_code'), 'administrative_sidos', ['sido_code'], unique=True)

    # 2. 새 테이블 생성: administrative_sggs (시군구)
    op.create_geospatial_table('administrative_sggs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sgg_code', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('sido_code', sqlmodel.sql.sqltypes.AutoString(length=2), nullable=False),
        sa.Column('geometry', Geometry(srid=4326, dimension=2, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_geospatial_index('idx_administrative_sggs_geometry', 'administrative_sggs', ['geometry'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_administrative_sggs_sgg_code'), 'administrative_sggs', ['sgg_code'], unique=True)
    op.create_index(op.f('ix_administrative_sggs_sido_code'), 'administrative_sggs', ['sido_code'], unique=False)

    # 3. 기존 데이터 마이그레이션: administrative_divisions → sido/sgg
    op.execute("""
        INSERT INTO administrative_sidos (created_at, sido_code, name, geometry)
        SELECT created_at, code, name, geometry
        FROM administrative_divisions
        WHERE level = 1
    """)
    op.execute("""
        INSERT INTO administrative_sggs (created_at, sgg_code, name, sido_code, geometry)
        SELECT created_at, code, name, parent_code, geometry
        FROM administrative_divisions
        WHERE level = 2
    """)

    # 4. administrative_emds: division_code → sgg_code
    op.add_column('administrative_emds', sa.Column('sgg_code', sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True))
    op.execute("UPDATE administrative_emds SET sgg_code = division_code")
    op.alter_column('administrative_emds', 'sgg_code', nullable=False)

    op.drop_index(op.f('ix_administrative_emds_division_code'), table_name='administrative_emds')
    op.drop_constraint('administrative_emds_division_code_fkey', 'administrative_emds', type_='foreignkey')
    op.drop_column('administrative_emds', 'division_code')

    op.create_index(op.f('ix_administrative_emds_sgg_code'), 'administrative_emds', ['sgg_code'], unique=False)
    op.create_foreign_key(None, 'administrative_emds', 'administrative_sggs', ['sgg_code'], ['sgg_code'])

    # 5. 구 테이블 삭제: administrative_divisions
    op.drop_geospatial_index(op.f('idx_administrative_divisions_geometry'), table_name='administrative_divisions', postgresql_using='gist', column_name='geometry')
    op.drop_index(op.f('ix_administrative_divisions_code'), table_name='administrative_divisions')
    op.drop_index(op.f('ix_administrative_divisions_parent_code'), table_name='administrative_divisions')
    op.drop_geospatial_table('administrative_divisions')


def downgrade() -> None:
    """Restore administrative_divisions from sido and sgg tables."""
    from sqlalchemy.dialects import postgresql

    # 1. 구 테이블 복원: administrative_divisions
    op.create_geospatial_table('administrative_divisions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('code', sa.VARCHAR(length=5), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('level', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('parent_code', sa.VARCHAR(length=5), autoincrement=False, nullable=True),
        sa.Column('geometry', Geometry(srid=4326, dimension=2, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry', _spatial_index_reflected=True), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('administrative_divisions_pkey')),
    )
    op.create_index(op.f('ix_administrative_divisions_parent_code'), 'administrative_divisions', ['parent_code'], unique=False)
    op.create_index(op.f('ix_administrative_divisions_code'), 'administrative_divisions', ['code'], unique=True)
    op.create_geospatial_index(op.f('idx_administrative_divisions_geometry'), 'administrative_divisions', ['geometry'], unique=False, postgresql_using='gist', postgresql_ops={})

    # 2. 데이터 복원: sido/sgg → administrative_divisions
    op.execute("""
        INSERT INTO administrative_divisions (created_at, code, name, level, parent_code, geometry)
        SELECT created_at, sido_code, name, 1, NULL, geometry
        FROM administrative_sidos
    """)
    op.execute("""
        INSERT INTO administrative_divisions (created_at, code, name, level, parent_code, geometry)
        SELECT created_at, sgg_code, name, 2, sido_code, geometry
        FROM administrative_sggs
    """)

    # 3. administrative_emds: sgg_code → division_code
    op.add_column('administrative_emds', sa.Column('division_code', sa.VARCHAR(length=5), autoincrement=False, nullable=True))
    op.execute("UPDATE administrative_emds SET division_code = sgg_code")
    op.alter_column('administrative_emds', 'division_code', nullable=False)

    op.drop_constraint(None, 'administrative_emds', type_='foreignkey')
    op.drop_index(op.f('ix_administrative_emds_sgg_code'), table_name='administrative_emds')
    op.drop_column('administrative_emds', 'sgg_code')

    op.create_foreign_key('administrative_emds_division_code_fkey', 'administrative_emds', 'administrative_divisions', ['division_code'], ['code'])
    op.create_index(op.f('ix_administrative_emds_division_code'), 'administrative_emds', ['division_code'], unique=False)

    # 4. 새 테이블 삭제
    op.drop_index(op.f('ix_administrative_sidos_sido_code'), table_name='administrative_sidos')
    op.drop_geospatial_index('idx_administrative_sidos_geometry', table_name='administrative_sidos', postgresql_using='gist', column_name='geometry')
    op.drop_geospatial_table('administrative_sidos')

    op.drop_index(op.f('ix_administrative_sggs_sido_code'), table_name='administrative_sggs')
    op.drop_index(op.f('ix_administrative_sggs_sgg_code'), table_name='administrative_sggs')
    op.drop_geospatial_index('idx_administrative_sggs_geometry', table_name='administrative_sggs', postgresql_using='gist', column_name='geometry')
    op.drop_geospatial_table('administrative_sggs')
