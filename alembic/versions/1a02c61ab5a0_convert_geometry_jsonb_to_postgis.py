"""convert geometry JSONB to PostGIS Geometry

Revision ID: 1a02c61ab5a0
Revises: fd10c95c1a9a
Create Date: 2026-02-16 12:00:00.000000

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1a02c61ab5a0"
down_revision: Union[str, Sequence[str], None] = "fd10c95c1a9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# geometry JSONB → PostGIS 변환 대상 테이블
TABLES = [
    "administrative_divisions",
    "administrative_emds",
    "lots",
    "road_center_lines",
    "use_region_districts",
    "gis_building_integrated",
]


def upgrade() -> None:
    """JSONB geometry 컬럼을 PostGIS Geometry(SRID=4326)로 변환합니다."""
    # PostGIS 확장 활성화
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    for table in TABLES:
        # 1. 새 PostGIS 컬럼 추가
        op.add_column(
            table,
            sa.Column(
                "geometry_new",
                geoalchemy2.Geometry(
                    geometry_type="GEOMETRY",
                    srid=4326,
                    spatial_index=False,
                ),
                nullable=True,
            ),
        )

        # 2. 기존 JSONB 데이터를 PostGIS Geometry로 변환
        op.execute(
            sa.text(
                f"UPDATE {table} "  # noqa: S608
                f"SET geometry_new = ST_SetSRID(ST_GeomFromGeoJSON(geometry::text), 4326) "
                f"WHERE geometry IS NOT NULL"
            )
        )

        # 3. 기존 JSONB 컬럼 삭제
        op.drop_column(table, "geometry")

        # 4. 새 컬럼 이름 변경
        op.alter_column(table, "geometry_new", new_column_name="geometry")

        # 5. 공간 인덱스 생성
        op.create_index(
            f"idx_{table}_geometry",
            table,
            ["geometry"],
            postgresql_using="gist",
        )


def downgrade() -> None:
    """PostGIS Geometry를 JSONB로 되돌립니다."""
    for table in TABLES:
        # 1. 공간 인덱스 삭제
        op.drop_index(f"idx_{table}_geometry", table_name=table)

        # 2. JSONB 임시 컬럼 추가
        op.add_column(
            table,
            sa.Column(
                "geometry_jsonb",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )

        # 3. PostGIS Geometry → GeoJSON 변환
        op.execute(
            sa.text(
                f"UPDATE {table} "  # noqa: S608
                f"SET geometry_jsonb = ST_AsGeoJSON(geometry)::jsonb "
                f"WHERE geometry IS NOT NULL"
            )
        )

        # 4. PostGIS 컬럼 삭제
        op.drop_column(table, "geometry")

        # 5. JSONB 컬럼 이름 변경
        op.alter_column(table, "geometry_jsonb", new_column_name="geometry")
