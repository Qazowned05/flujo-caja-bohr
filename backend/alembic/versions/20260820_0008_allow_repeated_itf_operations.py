"""allow repeated ITF operations

Revision ID: 20260820_0008
Revises: 20260819_0007
Create Date: 2026-08-20 00:08:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0008"
down_revision: Union[str, None] = "20260819_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_transaccion_cuenta_operacion", "transacciones", type_="unique")
    op.add_column(
        "transacciones",
        sa.Column("is_itf", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(
        "uq_transaccion_cuenta_operacion_non_itf",
        "transacciones",
        ["cuenta_bancaria_id", "n_operacion"],
        unique=True,
        postgresql_where=sa.text("is_itf = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_transaccion_cuenta_operacion_non_itf", table_name="transacciones")
    op.drop_column("transacciones", "is_itf")
    op.create_unique_constraint(
        "uq_transaccion_cuenta_operacion",
        "transacciones",
        ["cuenta_bancaria_id", "n_operacion"],
    )
