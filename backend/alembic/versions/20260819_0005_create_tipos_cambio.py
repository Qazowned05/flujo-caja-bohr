"""create tipos cambio

Revision ID: 20260819_0005
Revises: 20260819_0004
Create Date: 2026-08-19 00:05:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0005"
down_revision: Union[str, None] = "20260819_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tipos_cambio",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("moneda_origen", sa.String(length=3), nullable=False),
        sa.Column("moneda_destino", sa.String(length=3), nullable=False),
        sa.Column("tasa", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("fecha_vigencia", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "moneda_origen", "moneda_destino", "fecha_vigencia", name="uq_tipo_cambio_par_fecha"
        ),
    )


def downgrade() -> None:
    op.drop_table("tipos_cambio")
