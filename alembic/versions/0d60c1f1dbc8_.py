"""empty - tables already created in 6b002b37f1f7

Revision ID: 0d60c1f1dbc8
Revises: 1d756213b019
Create Date: 2026-02-17 21:19:10.203265

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '0d60c1f1dbc8'
down_revision: str | Sequence[str] | None = '1d756213b019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: ancillary_lands, land_and_forest_infos, land_ownerships already exist."""


def downgrade() -> None:
    """No-op."""
