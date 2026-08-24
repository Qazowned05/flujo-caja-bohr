import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.modules.shared.models import AuditAction, AuditLog
from app.modules.usuarios.models import User


def log_audit(
    db: Session,
    *,
    user: User,
    table: str,
    record_id: uuid.UUID,
    action: AuditAction,
    changes: dict[str, Any],
) -> None:
    """Stage an audit record in the same transaction as the mutation."""
    db.add(
        AuditLog(
            tabla=table,
            registro_id=record_id,
            accion=action,
            usuario_id=user.id,
            cambios=jsonable_encoder(changes),
        )
    )
