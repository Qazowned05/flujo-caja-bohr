"""remove profit and loss account fields

Revision ID: 20260909_0015
Revises: 20260909_0014
Create Date: 2026-09-09 00:15:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0015"
down_revision: Union[str, None] = "20260909_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM reglas_distribucion_resultado_lineas WHERE regla_id IN "
        "(SELECT id FROM reglas_distribucion_resultado WHERE rubro_id IS NULL)"
    )
    op.execute("DELETE FROM reglas_distribucion_resultado WHERE rubro_id IS NULL")
    op.drop_index("ix_reglas_distribucion_resultado_cuenta_contable", table_name="reglas_distribucion_resultado")
    op.drop_column("reglas_distribucion_resultado", "cuenta_contable")
    op.alter_column("reglas_distribucion_resultado", "rubro_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("asientos_resultado", "cuenta_contable", existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    raise NotImplementedError("Las cuentas contables se eliminaron intencionalmente.")
