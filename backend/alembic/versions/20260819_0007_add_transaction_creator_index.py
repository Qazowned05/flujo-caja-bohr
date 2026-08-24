"""add transaction creator index

Revision ID: 20260819_0007
Revises: 20260819_0006
Create Date: 2026-08-19 00:07:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260819_0007"
down_revision: Union[str, None] = "20260819_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_transacciones_created_by_id"), "transacciones", ["created_by_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_transacciones_created_by_id"), table_name="transacciones")
