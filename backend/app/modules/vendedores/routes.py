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
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User, UserRole
from app.modules.vendedores.models import Vendedor
from app.modules.vendedores.schemas import VendedorCreate, VendedorRead, VendedorUpdate

router = APIRouter(prefix="/vendedores", tags=["vendedores"])


def get_vendedor(db: Session, vendedor_id: uuid.UUID) -> Vendedor:
    record = db.get(Vendedor, vendedor_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendedor no encontrado.")
    return record


def validate_sucursal(db: Session, sucursal_id: uuid.UUID | None) -> None:
    if sucursal_id and (not (sucursal := db.get(Sucursal, sucursal_id)) or not sucursal.is_active):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sucursal activa no encontrada.",
        )


@router.get("", response_model=list[VendedorRead])
def list_vendedores(
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Vendedor]:
    if include_inactive and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    statement = select(Vendedor).order_by(Vendedor.nombre)
    if not include_inactive:
        statement = statement.where(Vendedor.is_active.is_(True))
    return list(db.scalars(statement))


@router.get("/{vendedor_id}", response_model=VendedorRead)
def read_vendedor(
    vendedor_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Vendedor:
    return get_vendedor(db, vendedor_id)


@router.post("", response_model=VendedorRead, status_code=status.HTTP_201_CREATED)
def create_vendedor(
    data: VendedorCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Vendedor:
    values = data.model_dump()
    validate_sucursal(db, values["sucursal_id"])
    if db.scalar(select(Vendedor).where(Vendedor.codigo == values["codigo"])):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de vendedor ya existe."
        )
    record = Vendedor(**values)
    db.add(record)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Vendedor.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes=values,
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{vendedor_id}", response_model=VendedorRead)
def update_vendedor(
    vendedor_id: uuid.UUID,
    data: VendedorUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Vendedor:
    record = get_vendedor(db, vendedor_id)
    values = data.model_dump(exclude_unset=True)
    if "sucursal_id" in values:
        validate_sucursal(db, values["sucursal_id"])
    if "codigo" in values and db.scalar(
        select(Vendedor).where(Vendedor.codigo == values["codigo"], Vendedor.id != vendedor_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de vendedor ya existe."
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
            table=Vendedor.__tablename__,
            record_id=record.id,
            action=AuditAction.UPDATE,
            changes=changes,
        )
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{vendedor_id}", response_model=VendedorRead)
def delete_vendedor(
    vendedor_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Vendedor:
    record = get_vendedor(db, vendedor_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El vendedor ya esta inactivo."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    log_audit(
        db,
        user=current_user,
        table=Vendedor.__tablename__,
        record_id=record.id,
        action=AuditAction.SOFT_DELETE,
        changes={"is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(record)
    return record
