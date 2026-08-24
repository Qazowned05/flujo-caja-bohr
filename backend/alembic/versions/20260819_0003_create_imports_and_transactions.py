"""create imports and transactions

Revision ID: 20260819_0003
Revises: 20260819_0002
Create Date: 2026-08-19 00:02:00
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260819_0003"
down_revision: Union[str, None] = "20260819_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    origen = sa.Enum("IMPORTADO", "PROYECCION", "MANUAL", name="origentransaccion")
    estado = sa.Enum(
        "PENDIENTE_TIPIFICAR", "TIPIFICADO", "PROYECTADO", "CONFIRMADO", name="estadotransaccion"
    )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cuenta_bancaria_id", sa.Uuid(), nullable=False),
        sa.Column("archivo_nombre", sa.String(length=255), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column(
            "fecha_importacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("total_filas", sa.Integer(), nullable=False),
        sa.Column("filas_nuevas", sa.Integer(), nullable=False),
        sa.Column("filas_duplicadas", sa.Integer(), nullable=False),
        sa.Column("filas_error", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cuenta_bancaria_id"], ["cuentas_bancarias.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_import_batches_cuenta_bancaria_id"), "import_batches", ["cuenta_bancaria_id"]
    )
    op.create_index(op.f("ix_import_batches_usuario_id"), "import_batches", ["usuario_id"])
    op.create_table(
        "transacciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("n_operacion", sa.String(length=255)),
        sa.Column("monto", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("documento", sa.String(length=255)),
        sa.Column("observaciones", sa.Text()),
        sa.Column("sucursal_id", sa.Uuid()),
        sa.Column("vendedor_id", sa.Uuid()),
        sa.Column("actividad_id", sa.Uuid()),
        sa.Column("concepto_id", sa.Uuid()),
        sa.Column("tipo_id", sa.Uuid()),
        sa.Column("cuenta_bancaria_id", sa.Uuid(), nullable=False),
        sa.Column("origen", origen, nullable=False),
        sa.Column("estado", estado, nullable=False),
        sa.Column("materializado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("import_batch_id", sa.Uuid()),
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
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursales.id"]),
        sa.ForeignKeyConstraint(["vendedor_id"], ["vendedores.id"]),
        sa.ForeignKeyConstraint(["actividad_id"], ["actividades.id"]),
        sa.ForeignKeyConstraint(["concepto_id"], ["conceptos.id"]),
        sa.ForeignKeyConstraint(["tipo_id"], ["tipos.id"]),
        sa.ForeignKeyConstraint(["cuenta_bancaria_id"], ["cuentas_bancarias.id"]),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cuenta_bancaria_id", "n_operacion", name="uq_transaccion_cuenta_operacion"
        ),
    )
    op.create_index(
        op.f("ix_transacciones_cuenta_bancaria_id"), "transacciones", ["cuenta_bancaria_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transacciones_cuenta_bancaria_id"), table_name="transacciones")
    op.drop_table("transacciones")
    sa.Enum(name="estadotransaccion").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="origentransaccion").drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f("ix_import_batches_usuario_id"), table_name="import_batches")
    op.drop_index(op.f("ix_import_batches_cuenta_bancaria_id"), table_name="import_batches")
    op.drop_table("import_batches")
