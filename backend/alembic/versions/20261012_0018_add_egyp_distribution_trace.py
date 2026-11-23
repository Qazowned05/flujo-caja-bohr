"""Store distribution details on result entries.

Revision ID: 20261012_0018
Revises: 20261001_0017
Create Date: 2026-10-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20261012_0018"
down_revision = "20261001_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asientos_resultado",
        sa.Column("regla_distribucion_nombre", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "asientos_resultado",
        sa.Column("porcentaje_distribucion", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("asientos_resultado", "porcentaje_distribucion")
    op.drop_column("asientos_resultado", "regla_distribucion_nombre")
