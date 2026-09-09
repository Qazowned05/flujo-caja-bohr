"""remove profit and loss account mappings

Revision ID: 20260909_0014
Revises: 20260908_0013
Create Date: 2026-09-09 00:01:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260909_0014"
down_revision: Union[str, None] = "20260908_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_mapeos_resultado_centro_resultado_id", table_name="mapeos_resultado")
    op.drop_index("ix_mapeos_resultado_rubro_id", table_name="mapeos_resultado")
    op.drop_index("ix_mapeos_resultado_cuenta_contable", table_name="mapeos_resultado")
    op.drop_table("mapeos_resultado")


def downgrade() -> None:
    raise NotImplementedError("Los mapeos de cuenta se eliminaron intencionalmente.")
