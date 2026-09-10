"""add hard delete audit action

Revision ID: 20260910_0016
Revises: 20260909_0015
Create Date: 2026-09-10 15:00:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260910_0016"
down_revision: Union[str, None] = "20260909_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'HARD_DELETE'")


def downgrade() -> None:
    pass
