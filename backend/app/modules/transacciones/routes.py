import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import CuentaBancaria
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.sucursales.models import Sucursal
from app.modules.transacciones.models import (
    EstadoTransaccion,
    OrigenTransaccion,
    Transaccion,
    TransaccionOperacion,
)
from app.modules.transacciones.schemas import (
    TransaccionListRead,
    TransaccionManualCreate,
    TransaccionMaterializar,
    TransaccionMultipleCreate,
    TransaccionMultipleUpdate,
    TransaccionProyeccionCreate,
    TransaccionRead,
    TransaccionUpdate,
)
from app.modules.usuarios.deps import get_current_user
from app.modules.usuarios.models import User, UserRole
from app.modules.vendedores.models import Vendedor

router = APIRouter(prefix="/transacciones", tags=["transacciones"])


def require_active(db: Session, model: Any, record_id: uuid.UUID, name: str) -> Any:
    record = db.get(model, record_id)
    if not record or not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{name} activo no encontrado.",
        )
    return record


def validate_references(db: Session, values: dict[str, Any]) -> None:
    for field, model, name in (
        ("sucursal_id", Sucursal, "Sucursal"),
        ("vendedor_id", Vendedor, "Vendedor"),
    ):
        if values.get(field) is not None:
            require_active(db, model, values[field], name)


def validate_categories(db: Session, categories: dict[str, uuid.UUID | None]) -> bool:
    category_values = tuple(categories.values())
    if not any(value is not None for value in category_values):
        return False
    if not all(value is not None for value in category_values):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="actividad_id, concepto_id y tipo_id deben enviarse juntos.",
        )
    actividad = require_active(db, Actividad, categories["actividad_id"], "Actividad")
    concepto = require_active(db, Concepto, categories["concepto_id"], "Concepto")
    tipo = require_active(db, Tipo, categories["tipo_id"], "Tipo")
    if concepto.actividad_id != actividad.id or tipo.concepto_id != concepto.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La jerarquia de tipificacion no es valida.",
        )
    return True


def effective_categories(
    transaction: Transaccion, values: dict[str, Any]
) -> dict[str, uuid.UUID | None]:
    return {
        field: values[field] if field in values else getattr(transaction, field)
        for field in ("actividad_id", "concepto_id", "tipo_id")
    }


def validate_operation_numbers(
    db: Session, account_id: uuid.UUID, numbers: list[str], transaction_id: uuid.UUID | None = None
) -> None:
    single_statement = select(Transaccion.n_operacion).where(
        Transaccion.cuenta_bancaria_id == account_id,
        Transaccion.n_operacion.in_(numbers),
        Transaccion.is_itf.is_(False),
    )
    multiple_statement = (
        select(TransaccionOperacion.numero)
        .join(Transaccion)
        .where(
            Transaccion.cuenta_bancaria_id == account_id,
            TransaccionOperacion.numero.in_(numbers),
        )
    )
    if transaction_id:
        single_statement = single_statement.where(Transaccion.id != transaction_id)
        multiple_statement = multiple_statement.where(Transaccion.id != transaction_id)
    duplicate = db.scalar(single_statement) or db.scalar(multiple_statement)
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una transaccion con el numero de operacion {duplicate} "
            "en la cuenta.",
        )


@router.post("/manual", response_model=TransaccionRead, status_code=status.HTTP_201_CREATED)
def create_manual(
    data: TransaccionManualCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    values = data.model_dump()
    account = require_active(db, CuentaBancaria, values["cuenta_bancaria_id"], "Cuenta bancaria")
    if values["n_operacion"] is not None and db.scalar(
        select(Transaccion).where(
            Transaccion.cuenta_bancaria_id == account.id,
            Transaccion.n_operacion == values["n_operacion"],
            Transaccion.is_itf.is_(False),
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una transaccion con ese numero de operacion en la cuenta.",
        )
    validate_references(db, values)
    has_categories = validate_categories(
        db,
        {field: values[field] for field in ("actividad_id", "concepto_id", "tipo_id")},
    )
    transaction = Transaccion(
        **values,
        moneda=account.moneda,
        origen=OrigenTransaccion.MANUAL,
        estado=(
            EstadoTransaccion.TIPIFICADO
            if has_categories
            else EstadoTransaccion.PENDIENTE_TIPIFICAR
        ),
        materializado=False,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(transaction)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.CREATE,
        changes={"origen": transaction.origen, "estado": transaction.estado},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una transaccion con ese numero de operacion en la cuenta.",
        ) from exc
    db.refresh(transaction)
    return transaction


@router.post("/multiple", response_model=TransaccionRead, status_code=status.HTTP_201_CREATED)
def create_multiple(
    data: TransaccionMultipleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    values = data.model_dump()
    operations = values.pop("operaciones")
    account = require_active(db, CuentaBancaria, values["cuenta_bancaria_id"], "Cuenta bancaria")
    validate_operation_numbers(db, account.id, operations)
    validate_references(db, values)
    has_categories = validate_categories(
        db, {field: values[field] for field in ("actividad_id", "concepto_id", "tipo_id")}
    )
    transaction = Transaccion(
        **values,
        n_operacion=None,
        moneda=account.moneda,
        origen=OrigenTransaccion.MULTIPLE,
        estado=(
            EstadoTransaccion.TIPIFICADO
            if has_categories
            else EstadoTransaccion.PENDIENTE_TIPIFICAR
        ),
        materializado=False,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        operaciones=[
            TransaccionOperacion(numero=number, orden=index)
            for index, number in enumerate(operations)
        ],
    )
    db.add(transaction)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.CREATE,
        changes={
            "origen": transaction.origen,
            "operaciones": operations,
            "estado": transaction.estado,
        },
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/proyeccion", response_model=TransaccionRead, status_code=status.HTTP_201_CREATED)
def create_proyeccion(
    data: TransaccionProyeccionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    values = data.model_dump()
    account = require_active(db, CuentaBancaria, values["cuenta_bancaria_id"], "Cuenta bancaria")
    validate_references(db, values)
    if not validate_categories(
        db,
        {field: values[field] for field in ("actividad_id", "concepto_id", "tipo_id")},
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Las proyecciones requieren actividad, concepto y tipo.",
        )
    transaction = Transaccion(
        **values,
        n_operacion=None,
        moneda=account.moneda,
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(transaction)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.CREATE,
        changes={"origen": transaction.origen, "estado": transaction.estado},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.patch("/{transaccion_id}/materializar", response_model=TransaccionRead)
def materializar_proyeccion(
    transaccion_id: uuid.UUID,
    data: TransaccionMaterializar,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    transaction = db.get(Transaccion, transaccion_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaccion no encontrada."
        )
    if transaction.origen != OrigenTransaccion.PROYECCION or transaction.materializado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden materializar proyecciones pendientes.",
        )

    values = data.model_dump(exclude_unset=True)
    operation = values.pop("n_operacion")
    duplicate = db.scalar(
        select(Transaccion).where(
            Transaccion.cuenta_bancaria_id == transaction.cuenta_bancaria_id,
            Transaccion.n_operacion == operation,
            Transaccion.is_itf.is_(False),
            Transaccion.id != transaction.id,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una transaccion con ese numero de operacion en la cuenta.",
        )
    validate_references(db, values)
    validate_categories(db, effective_categories(transaction, values))

    changes = {
        field: {"old": getattr(transaction, field), "new": value}
        for field, value in values.items()
        if getattr(transaction, field) != value
    }
    changes.update(
        {
            "n_operacion": {"old": transaction.n_operacion, "new": operation},
            "origen": {"old": transaction.origen, "new": OrigenTransaccion.MANUAL},
            "materializado": {"old": transaction.materializado, "new": True},
            "estado": {"old": transaction.estado, "new": EstadoTransaccion.CONFIRMADO},
        }
    )
    for field, value in values.items():
        setattr(transaction, field, value)
    transaction.n_operacion = operation
    transaction.origen = OrigenTransaccion.MANUAL
    transaction.materializado = True
    transaction.estado = EstadoTransaccion.CONFIRMADO
    transaction.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.UPDATE,
        changes=changes,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una transaccion con ese numero de operacion en la cuenta.",
        ) from exc
    db.refresh(transaction)
    return transaction


@router.get("", response_model=TransaccionListRead)
def list_transacciones(
    cuenta_bancaria_id: uuid.UUID | None = None,
    banco_id: uuid.UUID | None = None,
    moneda: str | None = Query(default=None, pattern=r"^[A-Za-z]{3}$"),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    actividad_id: uuid.UUID | None = None,
    concepto_id: uuid.UUID | None = None,
    tipo_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    estado: EstadoTransaccion | None = None,
    vendedor_id: uuid.UUID | None = None,
    sucursal_id: uuid.UUID | None = None,
    origen: OrigenTransaccion | None = None,
    con_documento: bool | None = None,
    busqueda: str | None = None,
    include_inactive: bool = False,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> TransaccionListRead:
    if include_inactive and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )

    filters = []
    if not include_inactive:
        filters.append(Transaccion.is_active.is_(True))
    if cuenta_bancaria_id:
        filters.append(Transaccion.cuenta_bancaria_id == cuenta_bancaria_id)
    if moneda:
        filters.append(Transaccion.moneda == moneda.upper())
    if fecha_desde:
        filters.append(Transaccion.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(Transaccion.fecha <= fecha_hasta)
    if actividad_id:
        filters.append(Transaccion.actividad_id == actividad_id)
    if concepto_id:
        filters.append(Transaccion.concepto_id == concepto_id)
    if tipo_id:
        filters.append(Transaccion.tipo_id == tipo_id)
    if created_by_id:
        filters.append(Transaccion.created_by_id == created_by_id)
    if estado:
        filters.append(Transaccion.estado == estado)
    if vendedor_id:
        filters.append(Transaccion.vendedor_id == vendedor_id)
    if sucursal_id:
        filters.append(Transaccion.sucursal_id == sucursal_id)
    if origen:
        filters.append(Transaccion.origen == origen)
    if con_documento is True:
        filters.extend([
            Transaccion.documento.is_not(None), func.trim(Transaccion.documento) != ""
        ])
    elif con_documento is False:
        filters.append(
            or_(Transaccion.documento.is_(None), func.trim(Transaccion.documento) == "")
        )
    if busqueda and busqueda.strip():
        term = f"%{busqueda.strip()}%"
        filters.append(
            or_(
                Transaccion.n_operacion.ilike(term),
                Transaccion.descripcion.ilike(term),
                Transaccion.id.in_(
                    select(TransaccionOperacion.transaccion_id).where(
                        TransaccionOperacion.numero.ilike(term)
                    )
                ),
            )
        )

    statement = select(Transaccion).options(
        selectinload(Transaccion.created_by),
        selectinload(Transaccion.updated_by),
        selectinload(Transaccion.operaciones),
    )
    count_statement = select(func.count()).select_from(Transaccion)
    if banco_id:
        statement = statement.join(CuentaBancaria)
        count_statement = count_statement.join(CuentaBancaria)
        filters.append(CuentaBancaria.banco_id == banco_id)
    statement = statement.where(*filters)
    total = db.scalar(count_statement.where(*filters)) or 0
    items = list(
        db.scalars(
            statement.order_by(Transaccion.fecha.desc(), Transaccion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return TransaccionListRead(items=items, total=total, offset=offset, limit=limit)


@router.get("/{transaccion_id}", response_model=TransaccionRead)
def get_transaccion(
    transaccion_id: uuid.UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    transaction = db.scalar(
        select(Transaccion)
        .options(
            selectinload(Transaccion.created_by),
            selectinload(Transaccion.updated_by),
            selectinload(Transaccion.operaciones),
        )
        .where(Transaccion.id == transaccion_id)
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaccion no encontrada."
        )
    return transaction


@router.patch("/{transaccion_id}/operaciones", response_model=TransaccionRead)
def update_multiple_operations(
    transaccion_id: uuid.UUID,
    data: TransaccionMultipleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    transaction = db.scalar(
        select(Transaccion)
        .options(selectinload(Transaccion.operaciones))
        .where(Transaccion.id == transaccion_id)
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaccion no encontrada."
        )
    if not transaction.is_active or transaction.origen != OrigenTransaccion.MULTIPLE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Solo se pueden editar operaciones de movimientos multiples activos.",
        )
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin puede editar numeros de operacion.",
        )
    operations = data.operaciones
    validate_operation_numbers(db, transaction.cuenta_bancaria_id, operations, transaction.id)
    previous = transaction.numeros_operacion
    transaction.operaciones.clear()
    db.flush()
    transaction.operaciones.extend(
        TransaccionOperacion(numero=number, orden=index) for index, number in enumerate(operations)
    )
    transaction.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.UPDATE,
        changes={"operaciones": {"old": previous, "new": operations}},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.patch("/{transaccion_id}", response_model=TransaccionRead)
def update_transaccion(
    transaccion_id: uuid.UUID,
    data: TransaccionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    transaction = db.get(Transaccion, transaccion_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaccion no encontrada."
        )
    if not transaction.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La transaccion esta anulada."
        )

    values = data.model_dump(exclude_unset=True)
    projection_id = values.pop("proyeccion_id", None)
    financial_fields = {"n_operacion", "monto"} & values.keys()
    if financial_fields and current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin puede editar monto o numero de operacion.",
        )
    if "n_operacion" in values:
        if transaction.origen in {OrigenTransaccion.PROYECCION, OrigenTransaccion.MULTIPLE}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Esta transaccion no tiene un unico numero de operacion editable.",
            )
        validate_operation_numbers(
            db,
            transaction.cuenta_bancaria_id,
            [values["n_operacion"]],
            transaction.id,
        )
    projection = None
    if projection_id:
        projection = db.get(Transaccion, projection_id)
        if (
            not projection
            or not projection.is_active
            or projection.origen != OrigenTransaccion.PROYECCION
            or projection.estado != EstadoTransaccion.PROYECTADO
            or projection.materializado
            or projection.cuenta_bancaria_id != transaction.cuenta_bancaria_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La proyeccion seleccionada no esta pendiente en la misma cuenta.",
            )
        if transaction.origen == OrigenTransaccion.PROYECCION:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Solo se puede asociar una proyeccion a un movimiento real.",
            )
    validate_references(db, values)
    resulting_categories = effective_categories(transaction, values)
    next_state: EstadoTransaccion | None = None
    has_categories = validate_categories(db, resulting_categories)
    if transaction.origen != OrigenTransaccion.PROYECCION:
        if has_categories:
            next_state = EstadoTransaccion.TIPIFICADO
        elif transaction.origen == OrigenTransaccion.IMPORTADO:
            next_state = EstadoTransaccion.PENDIENTE_TIPIFICAR

    changes = {
        field: {"old": getattr(transaction, field), "new": value}
        for field, value in values.items()
        if getattr(transaction, field) != value
    }
    if next_state is not None and transaction.estado != next_state:
        changes["estado"] = {"old": transaction.estado, "new": next_state}
    if projection:
        changes["proyeccion_asociada"] = {"id": projection.id}
    if not changes:
        db.refresh(transaction)
        return transaction

    for field, value in values.items():
        setattr(transaction, field, value)
    if next_state is not None:
        transaction.estado = next_state
    transaction.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.UPDATE,
        changes=changes,
    )
    if projection:
        projection.is_active = False
        projection.deleted_at = datetime.now(timezone.utc)
        projection.updated_by_id = current_user.id
        log_audit(
            db,
            user=current_user,
            table=Transaccion.__tablename__,
            record_id=projection.id,
            action=AuditAction.SOFT_DELETE,
            changes={
                "accion": "asociada_a_movimiento_real",
                "movimiento_real_id": str(transaction.id),
                "is_active": {"old": True, "new": False},
            },
        )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.patch("/{transaccion_id}/anular", response_model=TransaccionRead)
def anular_transaccion(
    transaccion_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Transaccion:
    if current_user.rol != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de admin."
        )
    transaction = db.get(Transaccion, transaccion_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaccion no encontrada."
        )
    if not transaction.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La transaccion ya esta anulada."
        )

    transaction.is_active = False
    transaction.deleted_at = datetime.now(timezone.utc)
    transaction.updated_by_id = current_user.id
    log_audit(
        db,
        user=current_user,
        table=Transaccion.__tablename__,
        record_id=transaction.id,
        action=AuditAction.SOFT_DELETE,
        changes={"accion": "anulado", "is_active": {"old": True, "new": False}},
    )
    db.commit()
    db.refresh(transaction)
    return transaction
