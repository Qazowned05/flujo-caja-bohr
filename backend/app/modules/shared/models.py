import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    SOFT_DELETE = "SOFT_DELETE"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tabla: Mapped[str] = mapped_column(String(100), index=True)
    registro_id: Mapped[uuid.UUID] = mapped_column(index=True)
    accion: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, values_callable=lambda actions: [action.value for action in actions])
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cambios: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
