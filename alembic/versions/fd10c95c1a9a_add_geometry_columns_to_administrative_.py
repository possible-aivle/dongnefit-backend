"""add geometry columns to administrative and lot tables

Revision ID: fd10c95c1a9a
Revises: 43819b90c398
Create Date: 2026-02-16 02:07:18.964522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fd10c95c1a9a'
down_revision: Union[str, Sequence[str], None] = '43819b90c398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('administrative_divisions', sa.Column('geometry', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('administrative_emds', sa.Column('geometry', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('lots', sa.Column('geometry', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lots', 'geometry')
    op.drop_column('administrative_emds', 'geometry')
    op.drop_column('administrative_divisions', 'geometry')
