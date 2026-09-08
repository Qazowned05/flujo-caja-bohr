"""create profit and loss module

Revision ID: 20260908_0012
Revises: 20260827_0011
Create Date: 2026-09-08 00:01:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_0012"
down_revision: Union[str, None] = "20260827_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def master_columns() -> list[sa.Column]:
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    naturaleza = sa.Enum(
        "INGRESO",
        "CONTRA_INGRESO",
        "COSTO_VENTA",
        "GASTO_OPERATIVO",
        "INGRESO_FINANCIERO",
        "GASTO_FINANCIERO",
        "IMPUESTO",
        name="naturalezarubro",
    )
    op.create_table(
        "centros_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("orden", sa.Integer(), server_default="0", nullable=False),
        *master_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index(
        op.f("ix_centros_resultado_codigo"), "centros_resultado", ["codigo"], unique=True
    )
    op.create_table(
        "rubros_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("naturaleza", naturaleza, nullable=False),
        sa.Column("padre_id", sa.Uuid(), nullable=True),
        sa.Column("orden", sa.Integer(), server_default="0", nullable=False),
        *master_columns(),
        sa.ForeignKeyConstraint(["padre_id"], ["rubros_resultado.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("padre_id", "nombre", name="uq_rubro_resultado_padre_nombre"),
    )
    op.create_index(op.f("ix_rubros_resultado_codigo"), "rubros_resultado", ["codigo"], unique=True)
    op.create_index(op.f("ix_rubros_resultado_padre_id"), "rubros_resultado", ["padre_id"])
    op.create_table(
        "mapeos_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cuenta_contable", sa.String(length=100), nullable=False),
        sa.Column("rubro_id", sa.Uuid(), nullable=False),
        sa.Column("centro_resultado_id", sa.Uuid(), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=True),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        *master_columns(),
        sa.ForeignKeyConstraint(["centro_resultado_id"], ["centros_resultado.id"]),
        sa.ForeignKeyConstraint(["rubro_id"], ["rubros_resultado.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mapeos_resultado_cuenta_contable"), "mapeos_resultado", ["cuenta_contable"]
    )
    op.create_index(op.f("ix_mapeos_resultado_rubro_id"), "mapeos_resultado", ["rubro_id"])
    op.create_index(
        op.f("ix_mapeos_resultado_centro_resultado_id"), "mapeos_resultado", ["centro_resultado_id"]
    )
    op.create_table(
        "lotes_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("archivo_nombre", sa.String(length=255), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column(
            "fecha_importacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("total_filas", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lotes_resultado_usuario_id"), "lotes_resultado", ["usuario_id"])
    op.create_table(
        "asientos_resultado",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cuenta_contable", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("documento", sa.String(length=255), nullable=True),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("debe", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("haber", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("centro_resultado_id", sa.Uuid(), nullable=True),
        sa.Column("rubro_id", sa.Uuid(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("lote_id", sa.Uuid(), nullable=True),
        sa.Column("numero_fila", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        *master_columns(),
        sa.ForeignKeyConstraint(["centro_resultado_id"], ["centros_resultado.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_resultado.id"]),
        sa.ForeignKeyConstraint(["rubro_id"], ["rubros_resultado.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lote_id", "numero_fila", name="uq_asiento_resultado_lote_fila"),
    )
    op.create_index(op.f("ix_asientos_resultado_fecha"), "asientos_resultado", ["fecha"])
    op.create_index(
        op.f("ix_asientos_resultado_cuenta_contable"), "asientos_resultado", ["cuenta_contable"]
    )
    op.create_index(
        op.f("ix_asientos_resultado_centro_resultado_id"),
        "asientos_resultado",
        ["centro_resultado_id"],
    )
    op.create_index(op.f("ix_asientos_resultado_rubro_id"), "asientos_resultado", ["rubro_id"])


def downgrade() -> None:
    for name in (
        "ix_asientos_resultado_rubro_id",
        "ix_asientos_resultado_centro_resultado_id",
        "ix_asientos_resultado_cuenta_contable",
        "ix_asientos_resultado_fecha",
    ):
        op.drop_index(name, table_name="asientos_resultado")
    op.drop_table("asientos_resultado")
    op.drop_index("ix_lotes_resultado_usuario_id", table_name="lotes_resultado")
    op.drop_table("lotes_resultado")
    for name in (
        "ix_mapeos_resultado_centro_resultado_id",
        "ix_mapeos_resultado_rubro_id",
        "ix_mapeos_resultado_cuenta_contable",
    ):
        op.drop_index(name, table_name="mapeos_resultado")
    op.drop_table("mapeos_resultado")
    op.drop_index("ix_rubros_resultado_padre_id", table_name="rubros_resultado")
    op.drop_index("ix_rubros_resultado_codigo", table_name="rubros_resultado")
    op.drop_table("rubros_resultado")
    op.drop_index("ix_centros_resultado_codigo", table_name="centros_resultado")
    op.drop_table("centros_resultado")
    sa.Enum(name="naturalezarubro").drop(op.get_bind(), checkfirst=True)
