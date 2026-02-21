"""rename_administrative_emds_code_to_emd_code

Revision ID: 42b7e2161ef4
Revises: 0d60c1f1dbc8
Create Date: 2026-02-17 21:32:01.186726

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '42b7e2161ef4'
down_revision: str | Sequence[str] | None = '0d60c1f1dbc8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename administrative_emds.code to emd_code."""
    op.drop_index(op.f('ix_administrative_emds_code'), table_name='administrative_emds')
    op.alter_column('administrative_emds', 'code', new_column_name='emd_code')
    op.create_index(op.f('ix_administrative_emds_emd_code'), 'administrative_emds', ['emd_code'], unique=True)


def downgrade() -> None:
    """Rename administrative_emds.emd_code back to code."""
    op.drop_index(op.f('ix_administrative_emds_emd_code'), table_name='administrative_emds')
    op.alter_column('administrative_emds', 'emd_code', new_column_name='code')
    op.create_index(op.f('ix_administrative_emds_code'), 'administrative_emds', ['code'], unique=True)
