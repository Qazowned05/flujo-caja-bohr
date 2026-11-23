"""decouple profit and loss distribution rules from categories

Revision ID: 20261001_0017
Revises: 20260910_0016
Create Date: 2026-10-01 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261001_0017"
down_revision: Union[str, None] = "20260910_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "reglas_distribucion_resultado_rubro_id_fkey",
        "reglas_distribucion_resultado",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_reglas_distribucion_resultado_rubro_id"),
        table_name="reglas_distribucion_resultado",
    )
    op.drop_column("reglas_distribucion_resultado", "rubro_id")


def downgrade() -> None:
    op.add_column(
        "reglas_distribucion_resultado", sa.Column("rubro_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "reglas_distribucion_resultado_rubro_id_fkey",
        "reglas_distribucion_resultado",
        "rubros_resultado",
        ["rubro_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_reglas_distribucion_resultado_rubro_id"),
        "reglas_distribucion_resultado",
        ["rubro_id"],
    )
