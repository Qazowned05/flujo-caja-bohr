import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from app.modules.usuarios.models import User


class OrigenTransaccion(str, enum.Enum):
    IMPORTADO = "IMPORTADO"
    PROYECCION = "PROYECCION"
    MANUAL = "MANUAL"


class EstadoTransaccion(str, enum.Enum):
    PENDIENTE_TIPIFICAR = "PENDIENTE_TIPIFICAR"
    TIPIFICADO = "TIPIFICADO"
    PROYECTADO = "PROYECTADO"
    CONFIRMADO = "CONFIRMADO"


class Transaccion(SoftDeleteMixin, Base):
    __tablename__ = "transacciones"
    __table_args__ = (
        Index(
            "uq_transaccion_cuenta_operacion_non_itf",
            "cuenta_bancaria_id",
            "n_operacion",
            unique=True,
            postgresql_where=text("is_itf = false"),
            sqlite_where=text("is_itf = 0"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    n_operacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_itf: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    documento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sucursales.id"), nullable=True, index=True
    )
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vendedores.id"), nullable=True, index=True
    )
    actividad_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("actividades.id"), nullable=True
    )
    concepto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("conceptos.id"), nullable=True)
    tipo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tipos.id"), nullable=True)
    cuenta_bancaria_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cuentas_bancarias.id"), index=True
    )
    origen: Mapped[OrigenTransaccion] = mapped_column(
        Enum(OrigenTransaccion, values_callable=lambda values: [value.value for value in values]),
        nullable=False,
    )
    estado: Mapped[EstadoTransaccion] = mapped_column(
        Enum(EstadoTransaccion, values_callable=lambda values: [value.value for value in values]),
        nullable=False,
        index=True,
    )
    materializado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batches.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped["User"] = relationship(foreign_keys=[updated_by_id])
