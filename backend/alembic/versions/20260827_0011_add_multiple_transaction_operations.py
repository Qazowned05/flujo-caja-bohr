"""add multiple transaction operations

Revision ID: 20260827_0011
Revises: 20260820_0010
Create Date: 2026-08-27 00:11:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0011"
down_revision: Union[str, None] = "20260820_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE origentransaccion ADD VALUE IF NOT EXISTS 'MULTIPLE'")
    op.create_table(
        "transaccion_operaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaccion_id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.String(length=255), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["transaccion_id"], ["transacciones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaccion_id", "numero"),
    )
    op.create_index(
        op.f("ix_transaccion_operaciones_transaccion_id"),
        "transaccion_operaciones",
        ["transaccion_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transaccion_operaciones_transaccion_id"), table_name="transaccion_operaciones")
    op.drop_table("transaccion_operaciones")
