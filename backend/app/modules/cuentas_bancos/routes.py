import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria
from app.modules.cuentas_bancos.schemas import (
    BancoCreate,
    BancoRead,
    BancoUpdate,
    CuentaBancariaCreate,
    CuentaBancariaRead,
    CuentaBancariaUpdate,
)
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User, UserRole

router = APIRouter(tags=["cuentas-bancarias"])


def allow_inactive(include_inactive: bool, current_user: User) -> bool:
    if include_inactive and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    return include_inactive


def active_bank(db: Session, bank_id: uuid.UUID) -> Banco:
    bank = db.get(Banco, bank_id)
    if not bank or not bank.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Banco activo no encontrado."
        )
    return bank


def require_record(db: Session, model: type[Banco] | type[CuentaBancaria], record_id: uuid.UUID):
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")
    return record


@router.get("/bancos", response_model=list[BancoRead])
def list_bancos(
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Banco]:
    statement = select(Banco).order_by(Banco.nombre)
    if not allow_inactive(include_inactive, current_user):
        statement = statement.where(Banco.is_active.is_(True))
    return list(db.scalars(statement))


@router.get("/bancos/{banco_id}", response_model=BancoRead)
def get_banco(
    banco_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Banco:
    return require_record(db, Banco, banco_id)


@router.post("/bancos", response_model=BancoRead, status_code=status.HTTP_201_CREATED)
def create_banco(
    data: BancoCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Banco:
    values = data.model_dump()
    if db.scalar(select(Banco).where(Banco.codigo == values["codigo"])):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de banco ya existe."
        )
    record = Banco(**values)
    db.add(record)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Banco.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes=values,
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch("/bancos/{banco_id}", response_model=BancoRead)
def update_banco(
    banco_id: uuid.UUID,
    data: BancoUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Banco:
    record = require_record(db, Banco, banco_id)
    values = data.model_dump(exclude_unset=True)
    if "codigo" in values and db.scalar(
        select(Banco).where(Banco.codigo == values["codigo"], Banco.id != banco_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de banco ya existe."
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
            table=Banco.__tablename__,
            record_id=record.id,
            action=AuditAction.UPDATE,
            changes=changes,
        )
    db.commit()
    db.refresh(record)
    return record


@router.delete("/bancos/{banco_id}", response_model=BancoRead)
def delete_banco(
    banco_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Banco:
    record = require_record(db, Banco, banco_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El banco ya esta inactivo."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    log_audit(
        db,
        user=current_user,
        table=Banco.__tablename__,
        record_id=record.id,
        action=AuditAction.SOFT_DELETE,
        changes={"is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(record)
    return record


@router.get("/cuentas-bancarias", response_model=list[CuentaBancariaRead])
def list_cuentas(
    banco_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[CuentaBancaria]:
    statement = select(CuentaBancaria).order_by(CuentaBancaria.alias)
    if banco_id:
        statement = statement.where(CuentaBancaria.banco_id == banco_id)
    if not allow_inactive(include_inactive, current_user):
        statement = statement.where(CuentaBancaria.is_active.is_(True))
    return list(db.scalars(statement))


@router.get("/cuentas-bancarias/{cuenta_id}", response_model=CuentaBancariaRead)
def get_cuenta(
    cuenta_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CuentaBancaria:
    return require_record(db, CuentaBancaria, cuenta_id)


@router.post(
    "/cuentas-bancarias", response_model=CuentaBancariaRead, status_code=status.HTTP_201_CREATED
)
def create_cuenta(
    data: CuentaBancariaCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CuentaBancaria:
    values = data.model_dump()
    active_bank(db, values["banco_id"])
    if db.scalar(
        select(CuentaBancaria).where(
            CuentaBancaria.banco_id == values["banco_id"],
            CuentaBancaria.numero_cuenta == values["numero_cuenta"],
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La cuenta ya existe para este banco."
        )
    record = CuentaBancaria(**values)
    db.add(record)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=CuentaBancaria.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes=values,
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch("/cuentas-bancarias/{cuenta_id}", response_model=CuentaBancariaRead)
def update_cuenta(
    cuenta_id: uuid.UUID,
    data: CuentaBancariaUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CuentaBancaria:
    record = require_record(db, CuentaBancaria, cuenta_id)
    values = data.model_dump(exclude_unset=True)
    bank_id = values.get("banco_id", record.banco_id)
    account_number = values.get("numero_cuenta", record.numero_cuenta)
    active_bank(db, bank_id)
    duplicate = db.scalar(
        select(CuentaBancaria).where(
            CuentaBancaria.banco_id == bank_id,
            CuentaBancaria.numero_cuenta == account_number,
            CuentaBancaria.id != cuenta_id,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La cuenta ya existe para este banco."
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
            table=CuentaBancaria.__tablename__,
            record_id=record.id,
            action=AuditAction.UPDATE,
            changes=changes,
        )
    db.commit()
    db.refresh(record)
    return record


@router.delete("/cuentas-bancarias/{cuenta_id}", response_model=CuentaBancariaRead)
def delete_cuenta(
    cuenta_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> CuentaBancaria:
    record = require_record(db, CuentaBancaria, cuenta_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La cuenta ya esta inactiva."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    log_audit(
        db,
        user=current_user,
        table=CuentaBancaria.__tablename__,
        record_id=record.id,
        action=AuditAction.SOFT_DELETE,
        changes={"is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(record)
    return record
