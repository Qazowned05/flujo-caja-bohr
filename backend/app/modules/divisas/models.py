import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin


class TipoCambio(SoftDeleteMixin, Base):
    __tablename__ = "tipos_cambio"
    __table_args__ = (
        UniqueConstraint(
            "moneda_origen", "moneda_destino", "fecha_vigencia", name="uq_tipo_cambio_par_fecha"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    moneda_origen: Mapped[str] = mapped_column(String(3), nullable=False)
    moneda_destino: Mapped[str] = mapped_column(String(3), nullable=False)
    tasa: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fecha_vigencia: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    updated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
