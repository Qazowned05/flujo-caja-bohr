import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cuenta_bancaria_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cuentas_bancarias.id"), index=True
    )
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha_importacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_nuevas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_duplicadas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
