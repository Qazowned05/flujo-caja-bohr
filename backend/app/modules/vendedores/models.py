import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.shared.mixins import SoftDeleteMixin


class Vendedor(SoftDeleteMixin, Base):
    __tablename__ = "vendedores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255))
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sucursales.id"), nullable=True, index=True
    )
