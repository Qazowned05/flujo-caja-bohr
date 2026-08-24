"""add transaction filter indexes

Revision ID: 20260819_0004
Revises: 20260819_0003
Create Date: 2026-08-19 00:04:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260819_0004"
down_revision: Union[str, None] = "20260819_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_transacciones_fecha"), "transacciones", ["fecha"])
    op.create_index(op.f("ix_transacciones_estado"), "transacciones", ["estado"])
    op.create_index(op.f("ix_transacciones_vendedor_id"), "transacciones", ["vendedor_id"])
    op.create_index(op.f("ix_transacciones_sucursal_id"), "transacciones", ["sucursal_id"])
    op.create_index(op.f("ix_transacciones_moneda"), "transacciones", ["moneda"])


def downgrade() -> None:
    op.drop_index(op.f("ix_transacciones_moneda"), table_name="transacciones")
    op.drop_index(op.f("ix_transacciones_sucursal_id"), table_name="transacciones")
    op.drop_index(op.f("ix_transacciones_vendedor_id"), table_name="transacciones")
    op.drop_index(op.f("ix_transacciones_estado"), table_name="transacciones")
    op.drop_index(op.f("ix_transacciones_fecha"), table_name="transacciones")
