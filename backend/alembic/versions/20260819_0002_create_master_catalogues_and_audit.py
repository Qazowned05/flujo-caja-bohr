"""create master catalogues and audit log

Revision ID: 20260819_0002
Revises: 20260819_0001
Create Date: 2026-08-19 00:01:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0002"
down_revision: Union[str, None] = "20260819_0001"
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
    op.create_table(
        "bancos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        *master_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bancos_codigo"), "bancos", ["codigo"], unique=True)
    op.create_table(
        "sucursales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        *master_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sucursales_codigo"), "sucursales", ["codigo"], unique=True)
    op.create_table(
        "actividades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        *master_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_actividades_nombre"), "actividades", ["nombre"], unique=True)
    op.create_table(
        "cuentas_bancarias",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("banco_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("numero_cuenta", sa.String(length=100), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        *master_columns(),
        sa.ForeignKeyConstraint(["banco_id"], ["bancos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("banco_id", "numero_cuenta", name="uq_cuenta_banco_numero"),
    )
    op.create_index(op.f("ix_cuentas_bancarias_banco_id"), "cuentas_bancarias", ["banco_id"])
    op.create_table(
        "vendedores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("sucursal_id", sa.Uuid(), nullable=True),
        *master_columns(),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vendedores_codigo"), "vendedores", ["codigo"], unique=True)
    op.create_index(op.f("ix_vendedores_sucursal_id"), "vendedores", ["sucursal_id"])
    op.create_table(
        "conceptos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actividad_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        *master_columns(),
        sa.ForeignKeyConstraint(["actividad_id"], ["actividades.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actividad_id", "nombre", name="uq_concepto_actividad_nombre"),
    )
    op.create_index(op.f("ix_conceptos_actividad_id"), "conceptos", ["actividad_id"])
    op.create_table(
        "tipos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concepto_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        *master_columns(),
        sa.ForeignKeyConstraint(["concepto_id"], ["conceptos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concepto_id", "nombre", name="uq_tipo_concepto_nombre"),
    )
    op.create_index(op.f("ix_tipos_concepto_id"), "tipos", ["concepto_id"])
    audit_action = sa.Enum("CREATE", "UPDATE", "SOFT_DELETE", name="auditaction")
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tabla", sa.String(length=100), nullable=False),
        sa.Column("registro_id", sa.Uuid(), nullable=False),
        sa.Column("accion", audit_action, nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("cambios", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_tabla"), "audit_logs", ["tabla"])
    op.create_index(op.f("ix_audit_logs_registro_id"), "audit_logs", ["registro_id"])
    op.create_index(op.f("ix_audit_logs_usuario_id"), "audit_logs", ["usuario_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_usuario_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_registro_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_tabla"), table_name="audit_logs")
    op.drop_table("audit_logs")
    sa.Enum(name="auditaction").drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f("ix_tipos_concepto_id"), table_name="tipos")
    op.drop_table("tipos")
    op.drop_index(op.f("ix_conceptos_actividad_id"), table_name="conceptos")
    op.drop_table("conceptos")
    op.drop_index(op.f("ix_vendedores_sucursal_id"), table_name="vendedores")
    op.drop_index(op.f("ix_vendedores_codigo"), table_name="vendedores")
    op.drop_table("vendedores")
    op.drop_index(op.f("ix_cuentas_bancarias_banco_id"), table_name="cuentas_bancarias")
    op.drop_table("cuentas_bancarias")
    op.drop_index(op.f("ix_actividades_nombre"), table_name="actividades")
    op.drop_table("actividades")
    op.drop_index(op.f("ix_sucursales_codigo"), table_name="sucursales")
    op.drop_table("sucursales")
    op.drop_index(op.f("ix_bancos_codigo"), table_name="bancos")
    op.drop_table("bancos")
