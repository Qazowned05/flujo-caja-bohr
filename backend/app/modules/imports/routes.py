import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import CuentaBancaria
from app.modules.imports.models import ImportBatch
from app.modules.imports.schemas import ImportBatchRead, ImportResponse
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.sucursales.models import Sucursal
from app.modules.transacciones.models import EstadoTransaccion, OrigenTransaccion, Transaccion
from app.modules.usuarios.deps import get_current_user
from app.modules.usuarios.models import User, UserRole
from app.modules.vendedores.models import Vendedor

router = APIRouter(prefix="/imports", tags=["imports"])

HEADERS = [
    "fecha",
    "descripcion",
    "n_operacion",
    "monto",
    "documento",
    "sucursal",
    "vendedor",
    "observaciones",
    "actividad",
    "concepto",
    "tipo",
]
PROJECTION_HEADERS = ["fecha", "descripcion", "monto", "actividad", "concepto", "tipo"]


@router.get("/plantilla.csv")
def download_template(tipo_importacion: Literal["REAL", "PROYECCION"] = "REAL") -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(PROJECTION_HEADERS if tipo_importacion == "PROYECCION" else HEADERS)
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                'attachment; filename="plantilla_proyecciones.csv"'
                if tipo_importacion == "PROYECCION"
                else 'attachment; filename="plantilla_importacion.csv"'
            )
        },
    )


class CSVValidationError(Exception):
    def __init__(self, errors: list[dict[str, object]]) -> None:
        self.payload = {
            "batch_id": None,
            "total_filas": 0,
            "filas_nuevas": 0,
            "filas_duplicadas": 0,
            "filas_error": len(errors),
            "duplicados": [],
            "errores": errors,
        }


def _parse_date(value: str) -> date | None:
    cleaned = value.strip().strip('"').strip("'").replace("\xa0", "")
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_csv(content: bytes, headers: list[str], is_projection: bool) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CSVValidationError(
            [{"fila": 0, "mensaje": "El archivo debe estar codificado en UTF-8."}]
        ) from exc
    try:
        reader: csv.DictReader | None = None
        for delim in (";", ","):
            candidate = csv.DictReader(io.StringIO(text), delimiter=delim)
            if candidate.fieldnames and candidate.fieldnames == headers:
                reader = candidate
                break
        if reader is None:
            raise CSVValidationError([{"fila": 1, "mensaje": "Las cabeceras no son validas."}])
        rows = list(reader)
    except csv.Error as exc:
        raise CSVValidationError([{"fila": 0, "mensaje": f"CSV invalido: {exc}"}]) from exc

    if not rows:
        raise CSVValidationError([{"fila": 2, "mensaje": "El archivo no contiene movimientos."}])

    errors: list[dict[str, object]] = []
    parsed: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        if None in row or all(not (value or "").strip() for value in row.values()):
            errors.append(
                {"fila": row_number, "mensaje": "No se permiten filas vacias o columnas extra."}
            )
            continue
        values = {key: (row.get(key) or "").strip() for key in headers}
        parsed_date = _parse_date(values["fecha"])
        if not parsed_date:
            errors.append(
                {
                    "fila": row_number,
                    "mensaje": "fecha debe tener formato DD/MM/AAAA (ej: 15/08/2026).",
                }
            )
            continue
        if not values["descripcion"]:
            errors.append(
                {"fila": row_number, "mensaje": "descripcion es obligatoria."}
            )
            continue
        if not is_projection and not values["n_operacion"]:
            errors.append({"fila": row_number, "mensaje": "n_operacion es obligatorio."})
            continue
        if is_projection and not all(
            values[field] for field in ("actividad", "concepto", "tipo")
        ):
            errors.append(
                {
                    "fila": row_number,
                    "mensaje": "actividad, concepto y tipo son obligatorios para proyecciones.",
                }
            )
            continue
        try:
            amount = Decimal(values["monto"].replace(",", "."))
        except (InvalidOperation, ValueError):
            errors.append({"fila": row_number, "mensaje": "monto debe ser un decimal valido."})
            continue
        if not amount.is_finite() or amount == 0:
            errors.append(
                {"fila": row_number, "mensaje": "monto debe ser finito y distinto de cero."}
            )
            continue
        parsed.append(
            {
                "fila": row_number,
                "fecha": parsed_date,
                "descripcion": values["descripcion"],
                "n_operacion": values.get("n_operacion") or None,
                "monto": amount,
                "documento": values.get("documento") or None,
                "sucursal": values.get("sucursal") or None,
                "vendedor": values.get("vendedor") or None,
                "observaciones": values.get("observaciones") or None,
                "actividad": values.get("actividad") or None,
                "concepto": values.get("concepto") or None,
                "tipo": values.get("tipo") or None,
            }
        )
    if errors:
        raise CSVValidationError(errors)
    return parsed


def _active_by_name(db: Session, model: Any, name: str) -> Any | None:
    records = list(
        db.scalars(select(model).where(model.nombre == name, model.is_active.is_(True)))
    )
    if len(records) != 1:
        return None
    return records[0]


def is_itf_movement(description: str) -> bool:
    return "itf" in description.casefold()


@router.post("/csv", response_model=ImportResponse)
def import_csv(
    cuenta_bancaria_id: Annotated[uuid.UUID, Form()],
    archivo: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    tipo_importacion: Annotated[Literal["REAL", "PROYECCION"], Form()] = "REAL",
) -> ImportResponse:
    try:
        if archivo.content_type and archivo.content_type not in {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
        }:
            raise CSVValidationError([{"fila": 0, "mensaje": "El archivo debe ser CSV."}])
        is_projection = tipo_importacion == "PROYECCION"
        rows = parse_csv(
            archivo.file.read(),
            PROJECTION_HEADERS if is_projection else HEADERS,
            is_projection,
        )
    except CSVValidationError as exc:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=exc.payload)

    account = db.get(CuentaBancaria, cuenta_bancaria_id)
    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cuenta bancaria activa no encontrada.",
        )

    normal_operations = [
        row["n_operacion"] for row in rows if not is_itf_movement(row["descripcion"])
    ]
    existing = (
        set(
            db.scalars(
                select(Transaccion.n_operacion).where(
                    Transaccion.cuenta_bancaria_id == cuenta_bancaria_id,
                    Transaccion.is_itf.is_(False),
                    Transaccion.n_operacion.in_(normal_operations),
                )
            )
        )
        if not is_projection
        else set()
    )
    duplicates: list[dict[str, object]] = []
    new_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        operation = str(row["n_operacion"])
        if is_projection or is_itf_movement(row["descripcion"]):
            new_rows.append(row)
        elif operation in existing:
            duplicates.append(
                {"fila": row["fila"], "n_operacion": operation, "motivo": "base_de_datos"}
            )
        elif operation in seen:
            duplicates.append({"fila": row["fila"], "n_operacion": operation, "motivo": "archivo"})
        else:
            seen.add(operation)
            new_rows.append(row)

    batch = ImportBatch(
        cuenta_bancaria_id=cuenta_bancaria_id,
        archivo_nombre=archivo.filename or "importacion.csv",
        usuario_id=current_user.id,
        total_filas=len(rows),
        filas_nuevas=len(new_rows),
        filas_duplicadas=len(duplicates),
        filas_error=0,
    )
    try:
        db.add(batch)
        db.flush()
        log_audit(
            db,
            user=current_user,
            table=ImportBatch.__tablename__,
            record_id=batch.id,
            action=AuditAction.CREATE,
            changes={"archivo_nombre": batch.archivo_nombre, "total_filas": batch.total_filas},
        )
        for row in new_rows:
            categories_ok = row.get("actividad") and row.get("concepto") and row.get("tipo")
            next_estado = EstadoTransaccion.PENDIENTE_TIPIFICAR
            actividad_id = None
            concepto_id = None
            tipo_id = None

            if categories_ok:
                actividad = _active_by_name(db, Actividad, row["actividad"])
                if not actividad:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Actividad activa no encontrada o duplicada: {row['actividad']}",
                    )
                concepto = db.scalar(
                    select(Concepto).where(
                        Concepto.nombre == row["concepto"],
                        Concepto.actividad_id == actividad.id,
                        Concepto.is_active.is_(True),
                    )
                )
                if not concepto:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Concepto activo no encontrado para la actividad "
                            f"'{row['actividad']}': {row['concepto']}"
                        ),
                    )
                tipo = db.scalar(
                    select(Tipo).where(
                        Tipo.nombre == row["tipo"],
                        Tipo.concepto_id == concepto.id,
                        Tipo.is_active.is_(True),
                    )
                )
                if not tipo:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=(
                            f"Tipo activo no encontrado para el concepto "
                            f"'{row['concepto']}': {row['tipo']}"
                        ),
                    )
                actividad_id = actividad.id
                concepto_id = concepto.id
                tipo_id = tipo.id
                next_estado = EstadoTransaccion.TIPIFICADO

            sucursal_id = None
            if not is_projection and row.get("sucursal"):
                sucursal = _active_by_name(db, Sucursal, row["sucursal"])
                if not sucursal:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Sucursal activa no encontrada o duplicada: {row['sucursal']}",
                    )
                sucursal_id = sucursal.id

            vendedor_id = None
            if not is_projection and row.get("vendedor"):
                vendedor = _active_by_name(db, Vendedor, row["vendedor"])
                if not vendedor:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Vendedor activo no encontrado o duplicado: {row['vendedor']}",
                    )
                vendedor_id = vendedor.id

            documento = (row["documento"] or "")[:255] or None
            transaction = Transaccion(
                fecha=row["fecha"],
                descripcion=row["descripcion"],
                n_operacion=None if is_projection else row["n_operacion"],
                is_itf=not is_projection and is_itf_movement(row["descripcion"]),
                monto=row["monto"],
                moneda=account.moneda,
                documento=None if is_projection else documento,
                observaciones=None if is_projection else row["observaciones"],
                sucursal_id=sucursal_id,
                vendedor_id=vendedor_id,
                actividad_id=actividad_id,
                concepto_id=concepto_id,
                tipo_id=tipo_id,
                cuenta_bancaria_id=account.id,
                origen=(
                    OrigenTransaccion.PROYECCION
                    if is_projection
                    else OrigenTransaccion.IMPORTADO
                ),
                estado=EstadoTransaccion.PROYECTADO if is_projection else next_estado,
                materializado=False,
                import_batch_id=batch.id,
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
                changes={"n_operacion": transaction.n_operacion, "monto": transaction.monto},
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conflicto de duplicados concurrente."
        ) from exc
    return ImportResponse(
        batch_id=batch.id,
        total_filas=batch.total_filas,
        filas_nuevas=batch.filas_nuevas,
        filas_duplicadas=batch.filas_duplicadas,
        filas_error=0,
        duplicados=duplicates,
        errores=[],
    )


@router.get("/{batch_id}", response_model=ImportBatchRead)
def get_batch(
    batch_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if not batch or (current_user.rol != UserRole.ADMIN and batch.usuario_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lote de importacion no encontrado."
        )
    return batch
