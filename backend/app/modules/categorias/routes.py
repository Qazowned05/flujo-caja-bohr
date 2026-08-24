import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.categorias.schemas import (
    ActividadCreate,
    ActividadRead,
    ActividadUpdate,
    ConceptoCreate,
    ConceptoRead,
    ConceptoUpdate,
    TipoCreate,
    TipoRead,
    TipoUpdate,
)
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User, UserRole

router = APIRouter(tags=["categorias"])


def require_record(db: Session, model: Any, record_id: uuid.UUID) -> Any:
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")
    return record


def require_active_actividad(db: Session, actividad_id: uuid.UUID) -> Actividad:
    record = require_record(db, Actividad, actividad_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Actividad activa no encontrada.",
        )
    return record


def require_active_concepto(db: Session, concepto_id: uuid.UUID) -> Concepto:
    record = require_record(db, Concepto, concepto_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Concepto activo no encontrado.",
        )
    require_active_actividad(db, record.actividad_id)
    return record


def list_statement(model: Any, include_inactive: bool, current_user: User):
    if include_inactive and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    statement = select(model).order_by(
        model.orden if model is Actividad else model.nombre,
        model.nombre,
    )
    return statement if include_inactive else statement.where(model.is_active.is_(True))


def save_change(
    db: Session, user: User, record: Any, action: AuditAction, changes: dict[str, Any]
) -> None:
    log_audit(
        db,
        user=user,
        table=record.__tablename__,
        record_id=record.id,
        action=action,
        changes=changes,
    )
    db.commit()
    db.refresh(record)


def apply_update(record: Any, values: dict[str, Any]) -> dict[str, Any]:
    changes = {
        field: {"old": getattr(record, field), "new": value}
        for field, value in values.items()
        if getattr(record, field) != value
    }
    for field, value in values.items():
        setattr(record, field, value)
    return changes


@router.get("/actividades", response_model=list[ActividadRead])
def list_actividades(
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Actividad]:
    return list(db.scalars(list_statement(Actividad, include_inactive, current_user)))


@router.get("/actividades/{actividad_id}", response_model=ActividadRead)
def read_actividad(
    actividad_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Actividad:
    return require_record(db, Actividad, actividad_id)


@router.post("/actividades", response_model=ActividadRead, status_code=status.HTTP_201_CREATED)
def create_actividad(
    data: ActividadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Actividad:
    values = data.model_dump()
    if db.scalar(select(Actividad).where(Actividad.nombre == values["nombre"])):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La actividad ya existe.")
    record = Actividad(**values)
    db.add(record)
    db.flush()
    save_change(db, current_user, record, AuditAction.CREATE, values)
    return record


@router.patch("/actividades/{actividad_id}", response_model=ActividadRead)
def update_actividad(
    actividad_id: uuid.UUID,
    data: ActividadUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Actividad:
    record = require_record(db, Actividad, actividad_id)
    values = data.model_dump(exclude_unset=True)
    if "nombre" in values and db.scalar(
        select(Actividad).where(Actividad.nombre == values["nombre"], Actividad.id != actividad_id)
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La actividad ya existe.")
    changes = apply_update(record, values)
    if changes:
        save_change(db, current_user, record, AuditAction.UPDATE, changes)
    else:
        db.refresh(record)
    return record


@router.delete("/actividades/{actividad_id}", response_model=ActividadRead)
def delete_actividad(
    actividad_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Actividad:
    record = require_active_actividad(db, actividad_id)
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    save_change(
        db,
        current_user,
        record,
        AuditAction.SOFT_DELETE,
        {"is_active": {"old": True, "new": False}},
    )
    return record


@router.get("/conceptos", response_model=list[ConceptoRead])
def list_conceptos(
    actividad_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Concepto]:
    statement = list_statement(Concepto, include_inactive, current_user)
    if actividad_id:
        statement = statement.where(Concepto.actividad_id == actividad_id)
    return list(db.scalars(statement))


@router.get("/conceptos/{concepto_id}", response_model=ConceptoRead)
def read_concepto(
    concepto_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Concepto:
    return require_record(db, Concepto, concepto_id)


@router.post("/conceptos", response_model=ConceptoRead, status_code=status.HTTP_201_CREATED)
def create_concepto(
    data: ConceptoCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Concepto:
    values = data.model_dump()
    require_active_actividad(db, values["actividad_id"])
    if db.scalar(
        select(Concepto).where(
            Concepto.actividad_id == values["actividad_id"], Concepto.nombre == values["nombre"]
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El concepto ya existe en esta actividad."
        )
    record = Concepto(**values)
    db.add(record)
    db.flush()
    save_change(db, current_user, record, AuditAction.CREATE, values)
    return record


@router.patch("/conceptos/{concepto_id}", response_model=ConceptoRead)
def update_concepto(
    concepto_id: uuid.UUID,
    data: ConceptoUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Concepto:
    record = require_record(db, Concepto, concepto_id)
    values = data.model_dump(exclude_unset=True)
    activity_id = values.get("actividad_id", record.actividad_id)
    require_active_actividad(db, activity_id)
    name = values.get("nombre", record.nombre)
    if db.scalar(
        select(Concepto).where(
            Concepto.actividad_id == activity_id,
            Concepto.nombre == name,
            Concepto.id != concepto_id,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El concepto ya existe en esta actividad."
        )
    changes = apply_update(record, values)
    if changes:
        save_change(db, current_user, record, AuditAction.UPDATE, changes)
    else:
        db.refresh(record)
    return record


@router.delete("/conceptos/{concepto_id}", response_model=ConceptoRead)
def delete_concepto(
    concepto_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Concepto:
    record = require_active_concepto(db, concepto_id)
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    save_change(
        db,
        current_user,
        record,
        AuditAction.SOFT_DELETE,
        {"is_active": {"old": True, "new": False}},
    )
    return record


@router.get("/tipos", response_model=list[TipoRead])
def list_tipos(
    concepto_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> list[Tipo]:
    statement = list_statement(Tipo, include_inactive, current_user)
    if concepto_id:
        statement = statement.where(Tipo.concepto_id == concepto_id)
    return list(db.scalars(statement))


@router.get("/tipos/{tipo_id}", response_model=TipoRead)
def read_tipo(
    tipo_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Tipo:
    return require_record(db, Tipo, tipo_id)


@router.post("/tipos", response_model=TipoRead, status_code=status.HTTP_201_CREATED)
def create_tipo(
    data: TipoCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Tipo:
    values = data.model_dump()
    require_active_concepto(db, values["concepto_id"])
    if db.scalar(
        select(Tipo).where(
            Tipo.concepto_id == values["concepto_id"], Tipo.nombre == values["nombre"]
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo ya existe en este concepto."
        )
    record = Tipo(**values)
    db.add(record)
    db.flush()
    save_change(db, current_user, record, AuditAction.CREATE, values)
    return record


@router.patch("/tipos/{tipo_id}", response_model=TipoRead)
def update_tipo(
    tipo_id: uuid.UUID,
    data: TipoUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Tipo:
    record = require_record(db, Tipo, tipo_id)
    values = data.model_dump(exclude_unset=True)
    parent_id = values.get("concepto_id", record.concepto_id)
    require_active_concepto(db, parent_id)
    name = values.get("nombre", record.nombre)
    if db.scalar(
        select(Tipo).where(Tipo.concepto_id == parent_id, Tipo.nombre == name, Tipo.id != tipo_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo ya existe en este concepto."
        )
    changes = apply_update(record, values)
    if changes:
        save_change(db, current_user, record, AuditAction.UPDATE, changes)
    else:
        db.refresh(record)
    return record


@router.delete("/tipos/{tipo_id}", response_model=TipoRead)
def delete_tipo(
    tipo_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Tipo:
    record = require_record(db, Tipo, tipo_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El tipo ya esta inactivo."
        )
    record.is_active = False
    record.deleted_at = datetime.now(UTC)
    save_change(
        db,
        current_user,
        record,
        AuditAction.SOFT_DELETE,
        {"is_active": {"old": True, "new": False}},
    )
    return record
