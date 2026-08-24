import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.divisas.models import TipoCambio
from app.modules.divisas.schemas import TipoCambioCreate, TipoCambioRead, TipoCambioUpdate
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User, UserRole

router = APIRouter(prefix="/divisas", tags=["divisas"])


def require_record(db: Session, record_id: uuid.UUID) -> TipoCambio:
    record = db.get(TipoCambio, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de cambio no encontrado."
        )
    return record


def duplicate(db: Session, values: dict[str, Any], exclude_id: uuid.UUID | None = None) -> bool:
    statement = select(TipoCambio).where(
        TipoCambio.moneda_origen == values["moneda_origen"],
        TipoCambio.moneda_destino == values["moneda_destino"],
        TipoCambio.fecha_vigencia == values["fecha_vigencia"],
    )
    if exclude_id:
        statement = statement.where(TipoCambio.id != exclude_id)
    return db.scalar(statement) is not None


@router.get("/tipos-cambio", response_model=list[TipoCambioRead])
def list_tipos_cambio(
    moneda_origen: str | None = None,
    moneda_destino: str | None = None,
    incluir_inactivos: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[TipoCambio]:
    if incluir_inactivos and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    statement = select(TipoCambio)
    if not incluir_inactivos:
        statement = statement.where(TipoCambio.is_active.is_(True))
    if moneda_origen:
        statement = statement.where(TipoCambio.moneda_origen == moneda_origen.upper())
    if moneda_destino:
        statement = statement.where(TipoCambio.moneda_destino == moneda_destino.upper())
    return list(db.scalars(statement.order_by(TipoCambio.fecha_vigencia.desc())))


@router.post("/tipos-cambio", response_model=TipoCambioRead, status_code=status.HTTP_201_CREATED)
def create_tipo_cambio(
    data: TipoCambioCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> TipoCambio:
    values = data.model_dump()
    if duplicate(db, values):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo de cambio ya existe."
        )
    record = TipoCambio(**values, created_by_id=current_user.id, updated_by_id=current_user.id)
    db.add(record)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=record.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes=values,
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch("/tipos-cambio/{tipo_cambio_id}", response_model=TipoCambioRead)
def update_tipo_cambio(
    tipo_cambio_id: uuid.UUID,
    data: TipoCambioUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> TipoCambio:
    record = require_record(db, tipo_cambio_id)
    values = data.model_dump(exclude_unset=True)
    pair = {
        field: values.get(field, getattr(record, field))
        for field in ("moneda_origen", "moneda_destino", "fecha_vigencia")
    }
    if pair["moneda_origen"] == pair["moneda_destino"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Las monedas deben ser distintas.",
        )
    if duplicate(db, pair, record.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo de cambio ya existe."
        )
    changes = {
        field: {"old": getattr(record, field), "new": value}
        for field, value in values.items()
        if getattr(record, field) != value
    }
    if not changes:
        return record
    for field, value in values.items():
        setattr(record, field, value)
    record.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=record.__tablename__,
        record_id=record.id,
        action=AuditAction.UPDATE,
        changes=changes,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo de cambio ya existe."
        ) from exc
    db.refresh(record)
    return record


@router.delete("/tipos-cambio/{tipo_cambio_id}", response_model=TipoCambioRead)
def delete_tipo_cambio(
    tipo_cambio_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> TipoCambio:
    record = require_record(db, tipo_cambio_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo de cambio ya esta inactivo."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    record.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=record.__tablename__,
        record_id=record.id,
        action=AuditAction.SOFT_DELETE,
        changes={"is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(record)
    return record
