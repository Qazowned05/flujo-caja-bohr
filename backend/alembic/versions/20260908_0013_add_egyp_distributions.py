"""add profit and loss distributions and manual entries

Revision ID: 20260908_0013
Revises: 20260908_0012
Create Date: 2026-09-08 00:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_0013"
down_revision: Union[str, None] = "20260908_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    origen = sa.Enum(
        "IMPORTADO", "BASE_GASTOS", "MANUAL", "DISTRIBUIDO", name="origenasientoresultado"
    )
    origen.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "reglas_distribucion_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("cuenta_contable", sa.String(length=100), nullable=True),
        sa.Column("rubro_id", sa.Uuid(), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=True),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["rubro_id"], ["rubros_resultado.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index(
        op.f("ix_reglas_distribucion_resultado_cuenta_contable"),
        "reglas_distribucion_resultado",
        ["cuenta_contable"],
    )
    op.create_index(
        op.f("ix_reglas_distribucion_resultado_rubro_id"),
        "reglas_distribucion_resultado",
        ["rubro_id"],
    )
    op.create_table(
        "reglas_distribucion_resultado_lineas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("regla_id", sa.Uuid(), nullable=False),
        sa.Column("centro_resultado_id", sa.Uuid(), nullable=False),
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=False),
        sa.ForeignKeyConstraint(["centro_resultado_id"], ["centros_resultado.id"]),
        sa.ForeignKeyConstraint(["regla_id"], ["reglas_distribucion_resultado.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regla_id", "centro_resultado_id"),
    )
    op.create_index(
        op.f("ix_reglas_distribucion_resultado_lineas_regla_id"),
        "reglas_distribucion_resultado_lineas",
        ["regla_id"],
    )
    op.create_index(
        op.f("ix_reglas_distribucion_resultado_lineas_centro_resultado_id"),
        "reglas_distribucion_resultado_lineas",
        ["centro_resultado_id"],
    )
    op.add_column(
        "asientos_resultado", sa.Column("origen", origen, server_default="MANUAL", nullable=False)
    )
    op.add_column("asientos_resultado", sa.Column("asiento_origen_id", sa.Uuid(), nullable=True))
    op.add_column(
        "asientos_resultado",
        sa.Column("es_resultado", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column("asientos_resultado", sa.Column("motivo_anulacion", sa.Text(), nullable=True))
    op.add_column("asientos_resultado", sa.Column("anulado_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_asientos_resultado_origen",
        "asientos_resultado",
        "asientos_resultado",
        ["asiento_origen_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_asientos_resultado_anulado_by",
        "asientos_resultado",
        "usuarios",
        ["anulado_by_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_asientos_resultado_asiento_origen_id"), "asientos_resultado", ["asiento_origen_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_asientos_resultado_asiento_origen_id"), table_name="asientos_resultado")
    op.drop_constraint("fk_asientos_resultado_anulado_by", "asientos_resultado", type_="foreignkey")
    op.drop_constraint("fk_asientos_resultado_origen", "asientos_resultado", type_="foreignkey")
    for column in (
        "anulado_by_id",
        "motivo_anulacion",
        "es_resultado",
        "asiento_origen_id",
        "origen",
    ):
        op.drop_column("asientos_resultado", column)
    op.drop_index(
        op.f("ix_reglas_distribucion_resultado_lineas_centro_resultado_id"),
        table_name="reglas_distribucion_resultado_lineas",
    )
    op.drop_index(
        op.f("ix_reglas_distribucion_resultado_lineas_regla_id"),
        table_name="reglas_distribucion_resultado_lineas",
    )
    op.drop_table("reglas_distribucion_resultado_lineas")
    op.drop_index(
        op.f("ix_reglas_distribucion_resultado_rubro_id"),
        table_name="reglas_distribucion_resultado",
    )
    op.drop_index(
        op.f("ix_reglas_distribucion_resultado_cuenta_contable"),
        table_name="reglas_distribucion_resultado",
    )
    op.drop_table("reglas_distribucion_resultado")
    sa.Enum(name="origenasientoresultado").drop(op.get_bind(), checkfirst=True)
