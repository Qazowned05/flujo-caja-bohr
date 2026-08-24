"""add saldo inicial to cuentas bancarias

Revision ID: 20260819_0006
Revises: 20260819_0005
Create Date: 2026-08-19 00:06:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0006"
down_revision: Union[str, None] = "20260819_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cuentas_bancarias",
        sa.Column(
            "saldo_inicial",
            sa.Numeric(precision=18, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("cuentas_bancarias", "saldo_inicial")
