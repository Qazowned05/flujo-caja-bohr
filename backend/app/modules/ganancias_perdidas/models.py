import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin


class NaturalezaRubro(str, enum.Enum):
    INGRESO = "INGRESO"
    CONTRA_INGRESO = "CONTRA_INGRESO"
    COSTO_VENTA = "COSTO_VENTA"
    GASTO_OPERATIVO = "GASTO_OPERATIVO"
    INGRESO_FINANCIERO = "INGRESO_FINANCIERO"
    GASTO_FINANCIERO = "GASTO_FINANCIERO"
    IMPUESTO = "IMPUESTO"


class OrigenAsientoResultado(str, enum.Enum):
    IMPORTADO = "IMPORTADO"
    BASE_GASTOS = "BASE_GASTOS"
    MANUAL = "MANUAL"
    DISTRIBUIDO = "DISTRIBUIDO"


class CentroResultado(SoftDeleteMixin, Base):
    __tablename__ = "centros_resultado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class RubroResultado(SoftDeleteMixin, Base):
    __tablename__ = "rubros_resultado"
    __table_args__ = (
        UniqueConstraint("padre_id", "nombre", name="uq_rubro_resultado_padre_nombre"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    naturaleza: Mapped[NaturalezaRubro] = mapped_column(
        Enum(NaturalezaRubro, values_callable=lambda values: [value.value for value in values]),
        nullable=False,
    )
    padre_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rubros_resultado.id"), nullable=True, index=True
    )
    orden: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class ReglaDistribucion(SoftDeleteMixin, Base):
    __tablename__ = "reglas_distribucion_resultado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    rubro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rubros_resultado.id"), index=True)
    vigente_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    lineas: Mapped[list["ReglaDistribucionLinea"]] = relationship(
        back_populates="regla",
        cascade="all, delete-orphan",
        order_by="ReglaDistribucionLinea.porcentaje",
    )


class ReglaDistribucionLinea(Base):
    __tablename__ = "reglas_distribucion_resultado_lineas"
    __table_args__ = (UniqueConstraint("regla_id", "centro_resultado_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    regla_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reglas_distribucion_resultado.id"), index=True
    )
    centro_resultado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("centros_resultado.id"), index=True
    )
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    regla: Mapped[ReglaDistribucion] = relationship(back_populates="lineas")


class LoteResultado(Base):
    __tablename__ = "lotes_resultado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha_importacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False)


class AsientoResultado(SoftDeleteMixin, Base):
    __tablename__ = "asientos_resultado"
    __table_args__ = (
        UniqueConstraint("lote_id", "numero_fila", name="uq_asiento_resultado_lote_fila"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cuenta_contable: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    documento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    debe: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    haber: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    centro_resultado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("centros_resultado.id"), nullable=True, index=True
    )
    rubro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rubros_resultado.id"), index=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    origen: Mapped[OrigenAsientoResultado] = mapped_column(
        Enum(
            OrigenAsientoResultado, values_callable=lambda values: [value.value for value in values]
        ),
        nullable=False,
        default=OrigenAsientoResultado.MANUAL,
        server_default="MANUAL",
    )
    asiento_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("asientos_resultado.id"), nullable=True, index=True
    )
    es_resultado: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    anulado_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    lote_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lotes_resultado.id"), nullable=True
    )
    numero_fila: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
