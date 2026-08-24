"""add activity order

Revision ID: 20260820_0010
Revises: 20260820_0009
Create Date: 2026-08-20 00:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0010"
down_revision: Union[str, None] = "20260820_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "actividades",
        sa.Column("orden", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("actividades", "orden")
