import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin


class Actividad(SoftDeleteMixin, Base):
    __tablename__ = "actividades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class Concepto(SoftDeleteMixin, Base):
    __tablename__ = "conceptos"
    __table_args__ = (
        UniqueConstraint("actividad_id", "nombre", name="uq_concepto_actividad_nombre"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actividad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("actividades.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    incluye_flujo_bruto_operativo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    incluye_flujo_neto_operativo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )


class Tipo(SoftDeleteMixin, Base):
    __tablename__ = "tipos"
    __table_args__ = (UniqueConstraint("concepto_id", "nombre", name="uq_tipo_concepto_nombre"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    concepto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conceptos.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
