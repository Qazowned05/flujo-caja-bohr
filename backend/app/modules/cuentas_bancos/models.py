import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin


class Banco(SoftDeleteMixin, Base):
    __tablename__ = "bancos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255))
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)


class CuentaBancaria(SoftDeleteMixin, Base):
    __tablename__ = "cuentas_bancarias"
    __table_args__ = (UniqueConstraint("banco_id", "numero_cuenta", name="uq_cuenta_banco_numero"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    banco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bancos.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255))
    numero_cuenta: Mapped[str] = mapped_column(String(100))
    moneda: Mapped[str] = mapped_column(String(3))
    saldo_inicial: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), server_default=text("0"), nullable=False
    )
