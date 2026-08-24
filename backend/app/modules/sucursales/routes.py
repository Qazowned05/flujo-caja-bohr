import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.sucursales.models import Sucursal
from app.modules.sucursales.schemas import SucursalCreate, SucursalRead, SucursalUpdate
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User, UserRole

router = APIRouter(prefix="/sucursales", tags=["sucursales"])


def get_sucursal(db: Session, sucursal_id: uuid.UUID) -> Sucursal:
    record = db.get(Sucursal, sucursal_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada.")
    return record


@router.get("", response_model=list[SucursalRead])
def list_sucursales(
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Sucursal]:
    if include_inactive and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    statement = select(Sucursal).order_by(Sucursal.nombre)
    if not include_inactive:
        statement = statement.where(Sucursal.is_active.is_(True))
    return list(db.scalars(statement))


@router.get("/{sucursal_id}", response_model=SucursalRead)
def read_sucursal(
    sucursal_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Sucursal:
    return get_sucursal(db, sucursal_id)


@router.post("", response_model=SucursalRead, status_code=status.HTTP_201_CREATED)
def create_sucursal(
    data: SucursalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Sucursal:
    values = data.model_dump()
    if db.scalar(select(Sucursal).where(Sucursal.codigo == values["codigo"])):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de sucursal ya existe."
        )
    record = Sucursal(**values)
    db.add(record)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Sucursal.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes=values,
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{sucursal_id}", response_model=SucursalRead)
def update_sucursal(
    sucursal_id: uuid.UUID,
    data: SucursalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Sucursal:
    record = get_sucursal(db, sucursal_id)
    values = data.model_dump(exclude_unset=True)
    if "codigo" in values and db.scalar(
        select(Sucursal).where(Sucursal.codigo == values["codigo"], Sucursal.id != sucursal_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de sucursal ya existe."
        )
    changes = {
        field: {"old": getattr(record, field), "new": value}
        for field, value in values.items()
        if getattr(record, field) != value
    }
    for field, value in values.items():
        setattr(record, field, value)
    if changes:
        log_audit(
            db,
            user=current_user,
            table=Sucursal.__tablename__,
            record_id=record.id,
            action=AuditAction.UPDATE,
            changes=changes,
        )
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{sucursal_id}", response_model=SucursalRead)
def delete_sucursal(
    sucursal_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Sucursal:
    record = get_sucursal(db, sucursal_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La sucursal ya esta inactiva."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    log_audit(
        db,
        user=current_user,
        table=Sucursal.__tablename__,
        record_id=record.id,
        action=AuditAction.SOFT_DELETE,
        changes={"is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(record)
    return record
