"""add operating flow concept flags

Revision ID: 20260820_0009
Revises: 20260820_0008
Create Date: 2026-08-20 00:09:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260820_0009"
down_revision: Union[str, None] = "20260820_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conceptos",
        sa.Column(
            "incluye_flujo_bruto_operativo",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "conceptos",
        sa.Column(
            "incluye_flujo_neto_operativo",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("conceptos", "incluye_flujo_neto_operativo")
    op.drop_column("conceptos", "incluye_flujo_bruto_operativo")
