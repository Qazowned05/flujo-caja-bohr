import uuid
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.ganancias_perdidas.models import (
    AsientoResultado,
    CentroResultado,
    LoteResultado,
    NaturalezaRubro,
    OrigenAsientoResultado,
    ReglaDistribucion,
    ReglaDistribucionLinea,
    RubroResultado,
)
from app.modules.ganancias_perdidas.schemas import (
    AsientoResultadoCreate,
    AsientosResultadoDelete,
    AsientoResultadoRead,
    AsientoResultadoUpdate,
    CentroResultadoCreate,
    CentroResultadoRead,
    CentroResultadoUpdate,
    ImportResultadoRead,
    ReglaDistribucionCreate,
    ReglaDistribucionRead,
    RentabilidadCentroResultadoRead,
    ResultadoRubroRead,
    ResumenGananciasPerdidasRead,
    RubroResultadoCreate,
    RubroResultadoRead,
    RubroResultadoUpdate,
    UltimoPeriodoResultadoRead,
)
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User

router = APIRouter(prefix="/ganancias-perdidas", tags=["ganancias-perdidas"])
ZERO = Decimal("0")
TEMPLATE_HEADERS = [
    "periodo",
    "rubro",
    "categoria",
    "monto_sin_igv",
    "centro_codigo",
    "regla_distribucion",
    "descripcion",
    "observaciones",
]


def require_enabled() -> None:
    if not settings.profit_and_loss_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modulo no habilitado.")


def require_record(db: Session, model: Any, record_id: uuid.UUID) -> Any:
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado.")
    return record


def require_active(db: Session, model: Any, record_id: uuid.UUID, label: str) -> Any:
    record = require_record(db, model, record_id)
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} activo no encontrado.",
        )
    return record


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


def active_statement(model: Any, include_inactive: bool):
    statement = select(model)
    return statement if include_inactive else statement.where(model.is_active.is_(True))


@router.get(
    "/centros", response_model=list[CentroResultadoRead], dependencies=[Depends(require_enabled)]
)
def list_centros(
    include_inactive: bool = False,
    _: Annotated[User, Depends(require_admin)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    return list(
        db.scalars(
            active_statement(CentroResultado, include_inactive).order_by(
                CentroResultado.orden, CentroResultado.nombre
            )
        )
    )


@router.post(
    "/centros",
    response_model=CentroResultadoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_enabled)],
)
def create_centro(
    data: CentroResultadoCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    values = data.model_dump()
    if db.scalar(
        select(CentroResultado).where(
            (CentroResultado.codigo == values["codigo"])
            | (CentroResultado.nombre == values["nombre"])
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El codigo o nombre de linea de negocio ya existe.",
        )
    record = CentroResultado(**values)
    db.add(record)
    db.flush()
    save_change(db, user, record, AuditAction.CREATE, values)
    return record


@router.patch(
    "/centros/{centro_id}",
    response_model=CentroResultadoRead,
    dependencies=[Depends(require_enabled)],
)
def update_centro(
    centro_id: uuid.UUID,
    data: CentroResultadoUpdate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_record(db, CentroResultado, centro_id)
    values = data.model_dump(exclude_unset=True)
    for field in ("codigo", "nombre"):
        if field in values and db.scalar(
            select(CentroResultado).where(
                getattr(CentroResultado, field) == values[field], CentroResultado.id != centro_id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"El {field} ya existe."
            )
    changes = apply_update(record, values)
    if changes:
        save_change(db, user, record, AuditAction.UPDATE, changes)
    return record


@router.delete(
    "/centros/{centro_id}",
    response_model=CentroResultadoRead,
    dependencies=[Depends(require_enabled)],
)
def delete_centro(
    centro_id: uuid.UUID,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_active(db, CentroResultado, centro_id, "Linea de negocio")
    record.is_active, record.deleted_at = False, datetime.now(UTC)
    save_change(
        db, user, record, AuditAction.SOFT_DELETE, {"is_active": {"old": True, "new": False}}
    )
    return record


@router.get(
    "/rubros", response_model=list[RubroResultadoRead], dependencies=[Depends(require_enabled)]
)
def list_rubros(
    include_inactive: bool = False,
    _: Annotated[User, Depends(require_admin)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    return list(
        db.scalars(
            active_statement(RubroResultado, include_inactive).order_by(
                RubroResultado.orden, RubroResultado.nombre
            )
        )
    )


@router.post(
    "/rubros",
    response_model=RubroResultadoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_enabled)],
)
def create_rubro(
    data: RubroResultadoCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    values = data.model_dump()
    if db.scalar(select(RubroResultado).where(RubroResultado.codigo == values["codigo"])):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de rubro ya existe."
        )
    if values["padre_id"]:
        require_active(db, RubroResultado, values["padre_id"], "Rubro padre")
    record = RubroResultado(**values)
    db.add(record)
    db.flush()
    save_change(db, user, record, AuditAction.CREATE, values)
    return record


@router.patch(
    "/rubros/{rubro_id}", response_model=RubroResultadoRead, dependencies=[Depends(require_enabled)]
)
def update_rubro(
    rubro_id: uuid.UUID,
    data: RubroResultadoUpdate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_record(db, RubroResultado, rubro_id)
    values = data.model_dump(exclude_unset=True)
    if "codigo" in values and db.scalar(
        select(RubroResultado).where(
            RubroResultado.codigo == values["codigo"], RubroResultado.id != rubro_id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo de rubro ya existe."
        )
    if values.get("padre_id"):
        if values["padre_id"] == rubro_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un rubro no puede ser su propio padre.",
            )
        require_active(db, RubroResultado, values["padre_id"], "Rubro padre")
    changes = apply_update(record, values)
    if changes:
        save_change(db, user, record, AuditAction.UPDATE, changes)
    return record


@router.delete(
    "/rubros/{rubro_id}", response_model=RubroResultadoRead, dependencies=[Depends(require_enabled)]
)
def delete_rubro(
    rubro_id: uuid.UUID,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_active(db, RubroResultado, rubro_id, "Rubro")
    if db.scalar(select(AsientoResultado.id).where(AsientoResultado.rubro_id == rubro_id).limit(1)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede inactivar un rubro con asientos.",
        )
    record.is_active, record.deleted_at = False, datetime.now(UTC)
    save_change(
        db, user, record, AuditAction.SOFT_DELETE, {"is_active": {"old": True, "new": False}}
    )
    return record


def validate_distribution(db: Session, values: ReglaDistribucionCreate) -> None:
    for line in values.lineas:
        require_active(db, CentroResultado, line.centro_resultado_id, "Linea de negocio")


@router.get(
    "/reglas-distribucion",
    response_model=list[ReglaDistribucionRead],
    dependencies=[Depends(require_enabled)],
)
def list_distribution_rules(
    include_inactive: bool = False,
    _: Annotated[User, Depends(require_admin)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    return list(
        db.scalars(
            active_statement(ReglaDistribucion, include_inactive).order_by(
                ReglaDistribucion.vigente_desde.desc(), ReglaDistribucion.nombre
            )
        )
    )


@router.post(
    "/reglas-distribucion",
    response_model=ReglaDistribucionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_enabled)],
)
def create_distribution_rule(
    data: ReglaDistribucionCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    if db.scalar(select(ReglaDistribucion).where(ReglaDistribucion.nombre == data.nombre)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La regla ya existe.")
    validate_distribution(db, data)
    values = data.model_dump(exclude={"lineas"})
    record = ReglaDistribucion(**values)
    record.lineas = [ReglaDistribucionLinea(**line.model_dump()) for line in data.lineas]
    db.add(record)
    db.flush()
    save_change(db, user, record, AuditAction.CREATE, data.model_dump(mode="json"))
    return record


@router.patch(
    "/reglas-distribucion/{regla_id}",
    response_model=ReglaDistribucionRead,
    dependencies=[Depends(require_enabled)],
)
def update_distribution_rule(
    regla_id: uuid.UUID,
    data: ReglaDistribucionCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_record(db, ReglaDistribucion, regla_id)
    duplicate = db.scalar(
        select(ReglaDistribucion).where(
            ReglaDistribucion.nombre == data.nombre, ReglaDistribucion.id != regla_id
        )
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La regla ya existe.")
    validate_distribution(db, data)
    changes = apply_update(record, data.model_dump(exclude={"lineas"}))
    previous_lines = [
        {"centro_resultado_id": str(line.centro_resultado_id), "porcentaje": str(line.porcentaje)}
        for line in record.lineas
    ]
    # Flush orphaned lines before inserting replacements to preserve the unique rule/center pair.
    record.lineas.clear()
    db.flush()
    record.lineas = [ReglaDistribucionLinea(**line.model_dump()) for line in data.lineas]
    changes["lineas"] = {"old": previous_lines, "new": data.model_dump(mode="json")["lineas"]}
    save_change(db, user, record, AuditAction.UPDATE, changes)
    return record


@router.delete(
    "/reglas-distribucion/{regla_id}",
    response_model=ReglaDistribucionRead,
    dependencies=[Depends(require_enabled)],
)
def delete_distribution_rule(
    regla_id: uuid.UUID,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_active(db, ReglaDistribucion, regla_id, "Regla")
    record.is_active, record.deleted_at = False, datetime.now(UTC)
    save_change(
        db, user, record, AuditAction.SOFT_DELETE, {"is_active": {"old": True, "new": False}}
    )
    return record


@router.get("/plantilla.xlsx", dependencies=[Depends(require_enabled)])
def download_template(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    incluir_asientos: bool = False,
):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Asientos"
    sheet.append(TEMPLATE_HEADERS)
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)
    sheet.freeze_panes = "A2"
    for column, width in {
        "A": 14,
        "B": 28,
        "C": 28,
        "D": 18,
        "E": 18,
        "F": 32,
        "G": 35,
        "H": 35,
    }.items():
        sheet.column_dimensions[column].width = width

    centers = list(
        db.scalars(
            select(CentroResultado)
            .where(CentroResultado.is_active.is_(True))
            .order_by(CentroResultado.orden)
        )
    )
    rubros = list(
        db.scalars(
            select(RubroResultado)
            .where(RubroResultado.is_active.is_(True))
            .order_by(RubroResultado.orden)
        )
    )
    parents = [rubro for rubro in rubros if rubro.padre_id is None]
    parent_by_id = {rubro.id: rubro for rubro in parents}
    if incluir_asientos:
        centers_by_id = {center.id: center for center in centers}
        rubros_by_id = {rubro.id: rubro for rubro in rubros}
        entries = list(
            db.scalars(
                select(AsientoResultado)
                .where(
                    AsientoResultado.is_active.is_(True),
                    AsientoResultado.asiento_origen_id.is_(None),
                )
                .order_by(AsientoResultado.fecha, AsientoResultado.created_at)
            )
        )
        entry_ids = [entry.id for entry in entries]
        distribution_rules = {
            origin_id: rule_name
            for origin_id, rule_name in db.execute(
                select(
                    AsientoResultado.asiento_origen_id,
                    AsientoResultado.regla_distribucion_nombre,
                ).where(
                    AsientoResultado.is_active.is_(True),
                    AsientoResultado.asiento_origen_id.in_(entry_ids),
                )
            )
            if origin_id and rule_name
        } if entry_ids else {}
        for entry in entries:
            category = rubros_by_id.get(entry.rubro_id)
            parent = parent_by_id.get(category.padre_id) if category else None
            if not category or not parent:
                continue
            center = centers_by_id.get(entry.centro_resultado_id)
            sheet.append(
                [
                    entry.fecha.strftime("%Y-%m"),
                    parent.nombre,
                    category.nombre,
                    max(entry.debe, entry.haber),
                    center.codigo if center else "",
                    distribution_rules.get(entry.id, ""),
                    entry.descripcion,
                    entry.observaciones or "",
                ]
            )
    else:
        sheet.append(
            [
                "2026-06",
                "Ingresos operativos",
                "Ingresos por venta",
                50000,
                "200",
                "",
                "Ventas junio",
                "",
            ]
        )
    centers_sheet = workbook.create_sheet("Lineas de negocio")
    centers_sheet.append(["codigo", "nombre"])
    for center in centers:
        centers_sheet.append([center.codigo, center.nombre])
    categories = [rubro for rubro in rubros if rubro.padre_id is not None]
    rubros_sheet = workbook.create_sheet("Rubros")
    rubros_sheet.append(["rubro", "categoria", "codigo_categoria", "naturaleza"])
    for category in categories:
        parent = parent_by_id.get(category.padre_id)
        if parent:
            rubros_sheet.append(
                [parent.nombre, category.nombre, category.codigo, category.naturaleza.value]
            )
    rules_sheet = workbook.create_sheet("Reglas distribucion")
    rules_sheet.append(
        [
            "regla",
            "centro",
            "porcentaje",
            "vigente_desde",
            "vigente_hasta",
        ]
    )
    for rule in db.scalars(select(ReglaDistribucion).where(ReglaDistribucion.is_active.is_(True))):
        for line in rule.lineas:
            rules_sheet.append(
                [
                    rule.nombre,
                    next((center.codigo for center in centers if center.id == line.centro_resultado_id), ""),
                    line.porcentaje,
                    rule.vigente_desde,
                    rule.vigente_hasta,
                ]
            )
    rule_options = [
        rule.nombre
        for rule in db.scalars(
            select(ReglaDistribucion)
            .where(ReglaDistribucion.is_active.is_(True))
            .order_by(ReglaDistribucion.nombre)
        )
    ]
    instructions = workbook.create_sheet("Guia de tipificacion")
    instructions.append(["Campo", "Uso"])
    instructions.append(["periodo", "Escribe solo mes y ano: 2026-06. El sistema usa el ultimo dia del mes."])
    instructions.append(["rubro", "Selecciona el rubro principal en la lista desplegable."])
    instructions.append(["categoria", "Selecciona la categoría disponible para el rubro elegido."])
    instructions.append(["monto_sin_igv", "Escribe siempre un monto positivo, sin IGV."])
    instructions.append(["centro_codigo", "Selecciona una linea para importes directos. Dejalo vacio si usaras una regla de distribución."])
    instructions.append(["regla_distribucion", "Opcional. Selecciona una regla vigente para distribuir el asiento. No la combines con centro_codigo."])
    instructions.append(["Calculo", "El sistema identifica automaticamente si el importe es ingreso, descuento, costo o gasto."])
    instructions.append(["Guias", "Las hojas Lineas de negocio, Rubros y Reglas distribucion son solo referencia."])
    center_validation = DataValidation(
        type="list", formula1=f"'Lineas de negocio'!$A$2:$A${max(2, len(centers) + 1)}", allow_blank=True
    )
    lists = workbook.create_sheet("Listas rubros")
    lists.append(["rubro", "rango_categorias"])
    lists.append(["", ""])
    workbook.defined_names.add(DefinedName("empty_category_list", attr_text="'Listas rubros'!$B$2"))
    category_groups: dict[str, list[str]] = {}
    for category in categories:
        parent = parent_by_id.get(category.padre_id)
        if parent:
            category_groups.setdefault(parent.nombre, []).append(category.nombre)
    list_column = 3
    for index, parent in enumerate(parents, start=1):
        range_name = f"egyp_category_options_{index}"
        names = sorted(category_groups.get(parent.nombre, []))
        column = get_column_letter(list_column)
        for row, name in enumerate(names, start=2):
            lists.cell(row=row, column=list_column, value=name)
        workbook.defined_names.add(
            DefinedName(
                range_name,
                attr_text=f"'Listas rubros'!${column}$2:${column}${max(2, len(names) + 1)}",
            )
        )
        lists.cell(row=index + 1, column=1, value=parent.nombre)
        lists.cell(row=index + 1, column=2, value=range_name)
        list_column += 1
    workbook.defined_names.add(
        DefinedName(
            "egyp_rubro_options",
            attr_text=f"'Listas rubros'!$A$2:$A${max(2, len(parents) + 1)}",
        )
    )
    rule_column = get_column_letter(list_column)
    for row, name in enumerate(rule_options, start=2):
        lists.cell(row=row, column=list_column, value=name)
    workbook.defined_names.add(
        DefinedName(
            "egyp_distribution_rule_options",
            attr_text=f"'Listas rubros'!${rule_column}$2:${rule_column}${max(2, len(rule_options) + 1)}",
        )
    )
    lists.sheet_state = "hidden"
    rubro_validation = DataValidation(type="list", formula1="=egyp_rubro_options", allow_blank=False)
    category_validation = DataValidation(
        type="list",
        formula1=(
            '=INDIRECT(IFERROR(VLOOKUP($B2,\'Listas rubros\'!$A$2:$B$'
            f'{max(2, len(parents) + 1)},2,FALSE),"empty_category_list"))'
        ),
        allow_blank=False,
    )
    rule_validation = DataValidation(
        type="list", formula1="=egyp_distribution_rule_options", allow_blank=True
    )
    for validation, target in (
        (rubro_validation, "B2:B5000"),
        (category_validation, "C2:C5000"),
        (center_validation, "E2:E5000"),
        (rule_validation, "F2:F5000"),
    ):
        sheet.add_data_validation(validation)
        validation.add(target)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                "attachment; filename=asientos_egyp.xlsx"
                if incluir_asientos
                else "attachment; filename=plantilla_egyp.xlsx"
            )
        },
    )


def resolve_row(
    db: Session, values: dict[str, Any], row_number: int
) -> tuple[RubroResultado, CentroResultado | None, ReglaDistribucion | None]:
    if not values["rubro"]:
        raise ValueError(f"Fila {row_number}: rubro es obligatorio.")
    if not values["categoria"]:
        raise ValueError(f"Fila {row_number}: categoria es obligatoria.")
    parent = db.scalar(
        select(RubroResultado).where(
            RubroResultado.nombre == values["rubro"],
            RubroResultado.padre_id.is_(None),
            RubroResultado.is_active.is_(True),
        )
    )
    rubro = (
        db.scalar(
            select(RubroResultado).where(
                RubroResultado.nombre == values["categoria"],
                RubroResultado.padre_id == parent.id,
                RubroResultado.is_active.is_(True),
            )
        )
        if parent
        else None
    )
    centro = None
    if values["centro_codigo"]:
        centro = db.scalar(
            select(CentroResultado).where(
                CentroResultado.codigo == values["centro_codigo"],
                CentroResultado.is_active.is_(True),
            )
        )
    if not rubro:
        raise ValueError(
            f"Fila {row_number}: categoria no corresponde al rubro seleccionado o esta inactiva."
        )
    if values["centro_codigo"] and not centro:
        raise ValueError(f"Fila {row_number}: centro_codigo no existe o esta inactivo.")
    rule_name = values.get("regla_distribucion", "")
    if values["centro_codigo"] and rule_name:
        raise ValueError(f"Fila {row_number}: usa centro_codigo o regla_distribucion, no ambos.")
    rule = selected_distribution_rule(db, values["fecha"], rule_name)
    if not centro and not rule:
        raise ValueError(
            f"Fila {row_number}: selecciona centro_codigo o regla_distribucion."
        )
    return rubro, centro, rule


def selected_distribution_rule(
    db: Session, entry_date: date, rule_name: str
) -> ReglaDistribucion | None:
    if not rule_name:
        return None
    rule = db.scalar(select(ReglaDistribucion).where(ReglaDistribucion.nombre == rule_name))
    if not rule or not rule.is_active:
        raise ValueError("regla_distribucion no existe o esta inactiva.")
    if (rule.vigente_desde and rule.vigente_desde > entry_date) or (
        rule.vigente_hasta and rule.vigente_hasta < entry_date
    ):
        raise ValueError("regla_distribucion no está vigente para el período indicado.")
    return rule


def create_entry(
    db: Session,
    user: User,
    values: dict[str, Any],
    rubro: RubroResultado,
    centro: CentroResultado | None,
    origen: OrigenAsientoResultado,
    lote_id: uuid.UUID | None = None,
    numero_fila: int | None = None,
    distribution_rule: ReglaDistribucion | None = None,
) -> AsientoResultado:
    entry_values = {
        key: values[key]
        for key in (
            "fecha",
            "descripcion",
            "documento",
            "moneda",
            "debe",
            "haber",
            "observaciones",
        )
    }
    if centro:
        entry = AsientoResultado(
            **entry_values,
            rubro_id=rubro.id,
            centro_resultado_id=centro.id,
            origen=origen,
            lote_id=lote_id,
            numero_fila=numero_fila,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(entry)
        return entry
    rule = distribution_rule
    if not rule:
        entry = AsientoResultado(
            **entry_values,
            rubro_id=rubro.id,
            origen=origen,
            lote_id=lote_id,
            numero_fila=numero_fila,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
        db.add(entry)
        return entry
    origin_entry = AsientoResultado(
        **entry_values,
        rubro_id=rubro.id,
        origen=origen,
        es_resultado=False,
        lote_id=lote_id,
        numero_fila=numero_fila,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(origin_entry)
    db.flush()
    remaining_debe, remaining_haber = Decimal(values["debe"]), Decimal(values["haber"])
    for index, line in enumerate(rule.lineas):
        is_last = index == len(rule.lineas) - 1
        debe = (
            remaining_debe
            if is_last
            else (Decimal(values["debe"]) * Decimal(line.porcentaje) / 100).quantize(
                Decimal("0.01")
            )
        )
        haber = (
            remaining_haber
            if is_last
            else (Decimal(values["haber"]) * Decimal(line.porcentaje) / 100).quantize(
                Decimal("0.01")
            )
        )
        remaining_debe -= debe
        remaining_haber -= haber
        db.add(
            AsientoResultado(
                **{**entry_values, "debe": debe, "haber": haber},
                rubro_id=rubro.id,
                centro_resultado_id=line.centro_resultado_id,
                origen=OrigenAsientoResultado.DISTRIBUIDO,
                asiento_origen_id=origin_entry.id,
                regla_distribucion_nombre=rule.nombre,
                porcentaje_distribucion=line.porcentaje,
                lote_id=lote_id,
                created_by_id=user.id,
                updated_by_id=user.id,
            )
        )
    return origin_entry


@router.post(
    "/importar.xlsx",
    response_model=ImportResultadoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_enabled)],
)
async def import_asientos(
    archivo: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    if not (archivo.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El archivo debe ser .xlsx."
        )
    try:
        workbook = load_workbook(BytesIO(await archivo.read()), read_only=True, data_only=True)
        sheet = workbook["Asientos"]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo leer la hoja Asientos.",
        ) from exc
    headers = [
        str(value or "").strip()
        for value in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
    ]
    if headers != TEMPLATE_HEADERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Las cabeceras de la hoja Asientos no coinciden con la plantilla.",
        )
    parsed: list[dict[str, Any]] = []
    errors: list[dict[str, object]] = []
    for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not any(value is not None and str(value).strip() for value in row):
            continue
        try:
            raw = dict(zip(TEMPLATE_HEADERS, row, strict=True))
            period = str(raw["periodo"] or "").strip()
            if len(period) != 7 or period[4] != "-":
                raise ValueError("periodo debe tener formato AAAA-MM.")
            year, month = (int(value) for value in period.split("-"))
            entry_date = date(year, month, monthrange(year, month)[1])
            amount = Decimal(str(raw["monto_sin_igv"] or 0))
            if amount <= ZERO:
                raise ValueError("monto_sin_igv debe ser mayor que cero.")
            values = {
                "fecha": entry_date,
                "centro_codigo": str(raw["centro_codigo"] or "").strip(),
                "regla_distribucion": str(raw["regla_distribucion"] or "").strip(),
                "rubro": str(raw["rubro"] or "").strip(),
                "categoria": str(raw["categoria"] or "").strip(),
                "numero_fila": row_number,
            }
            rubro, _, _ = resolve_row(db, values, row_number)
            credit = rubro.naturaleza in {
                NaturalezaRubro.INGRESO,
                NaturalezaRubro.INGRESO_FINANCIERO,
            }
            parsed.append(
                {
                    **values,
                    "descripcion": str(raw["descripcion"] or "").strip() or rubro.nombre,
                    "documento": f"Cierre {period}",
                    "moneda": "PEN",
                    "debe": ZERO if credit else amount,
                    "haber": amount if credit else ZERO,
                    "observaciones": str(raw["observaciones"] or "").strip() or None,
                }
            )
        except (ValueError, TypeError, ArithmeticError) as exc:
            errors.append({"fila": row_number, "mensaje": str(exc)})
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errores": errors}
        )
    batch = LoteResultado(
        archivo_nombre=archivo.filename or "asientos.xlsx",
        usuario_id=user.id,
        total_filas=len(parsed),
    )
    db.add(batch)
    db.flush()
    for row in parsed:
        rubro, centro, rule = resolve_row(db, row, row["numero_fila"])
        create_entry(
            db,
            user,
            row,
            rubro,
            centro,
            OrigenAsientoResultado.IMPORTADO,
            batch.id,
            row["numero_fila"],
            rule,
        )
    log_audit(
        db,
        user=user,
        table=batch.__tablename__,
        record_id=batch.id,
        action=AuditAction.CREATE,
        changes={"archivo_nombre": batch.archivo_nombre, "total_filas": len(parsed)},
    )
    db.commit()
    return ImportResultadoRead(lote_id=batch.id, total_filas=len(parsed), filas_nuevas=len(parsed))


@router.post(
    "/asientos",
    response_model=AsientoResultadoRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_enabled)],
)
def create_manual_entry(
    data: AsientoResultadoCreate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    rubro = require_active(db, RubroResultado, data.rubro_id, "Rubro")
    centro = (
        require_active(db, CentroResultado, data.centro_resultado_id, "Linea de negocio")
        if data.centro_resultado_id
        else None
    )
    rule = (
        require_active(db, ReglaDistribucion, data.regla_distribucion_id, "Regla de distribución")
        if data.regla_distribucion_id
        else None
    )
    if not centro and not rule:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona una linea de negocio o una regla de distribución.",
        )
    record = create_entry(
        db, user, data.model_dump(), rubro, centro, OrigenAsientoResultado.MANUAL, distribution_rule=rule
    )
    db.flush()
    log_audit(
        db,
        user=user,
        table=record.__tablename__,
        record_id=record.id,
        action=AuditAction.CREATE,
        changes={"origen": OrigenAsientoResultado.MANUAL.value, **data.model_dump(mode="json")},
    )
    db.commit()
    db.refresh(record)
    return record


@router.patch(
    "/asientos/{asiento_id}",
    response_model=AsientoResultadoRead,
    dependencies=[Depends(require_enabled)],
)
def update_manual_entry(
    asiento_id: uuid.UUID,
    data: AsientoResultadoUpdate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_active(db, AsientoResultado, asiento_id, "Asiento")
    if not record.es_resultado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pueden editar las líneas distribuidas. Edita el asiento de origen.",
        )
    values = data.model_dump(exclude_unset=True)
    merged = {
        field: values.get(field, getattr(record, field))
        for field in AsientoResultadoCreate.model_fields
        if field != "regla_distribucion_id"
    }
    merged["regla_distribucion_id"] = values.get("regla_distribucion_id")
    if merged["debe"] == ZERO and merged["haber"] == ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe u haber es obligatorio."
        )
    require_active(db, RubroResultado, merged["rubro_id"], "Rubro")
    if merged["centro_resultado_id"]:
        require_active(db, CentroResultado, merged["centro_resultado_id"], "Linea de negocio")
    elif merged["regla_distribucion_id"]:
        require_active(
            db, ReglaDistribucion, merged["regla_distribucion_id"], "Regla de distribución"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona una linea de negocio o una regla de distribución.",
        )
    changes = apply_update(record, values)
    if changes:
        record.updated_by_id = user.id
        save_change(db, user, record, AuditAction.UPDATE, changes)
    return record


@router.delete(
    "/asientos",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_enabled)],
)
def hard_delete_entries(
    data: AsientosResultadoDelete,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    records = list(
        db.scalars(
            select(AsientoResultado).where(
                AsientoResultado.id.in_(set(data.ids)), AsientoResultado.is_active.is_(True)
            )
        )
    )
    if len(records) != len(set(data.ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uno o más asientos no existen.")
    origin_ids = {record.asiento_origen_id or record.id for record in records}
    entries = list(
        db.scalars(
            select(AsientoResultado).where(
                or_(
                    AsientoResultado.id.in_(origin_ids),
                    AsientoResultado.asiento_origen_id.in_(origin_ids),
                )
            )
        )
    )
    db.execute(delete(AsientoResultado).where(AsientoResultado.asiento_origen_id.in_(origin_ids)))
    db.execute(delete(AsientoResultado).where(AsientoResultado.id.in_(origin_ids)))
    log_audit(
        db,
        user=user,
        table=AsientoResultado.__tablename__,
        record_id=next(iter(origin_ids)),
        action=AuditAction.HARD_DELETE,
        changes={
            "asientos_eliminados": [str(entry.id) for entry in entries],
            "eliminacion_masiva": True,
        },
    )
    db.commit()


@router.delete(
    "/asientos/{asiento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_enabled)],
)
def hard_delete_entry(
    asiento_id: uuid.UUID,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    record = require_active(db, AsientoResultado, asiento_id, "Asiento")
    origin_id = record.asiento_origen_id or record.id
    entries = list(
        db.scalars(
            select(AsientoResultado).where(
                or_(
                    AsientoResultado.id == origin_id,
                    AsientoResultado.asiento_origen_id == origin_id,
                )
            )
        )
    )
    # PostgreSQL enforces the self-reference immediately, so derived entries
    # must be removed before the origin entry.
    db.execute(
        delete(AsientoResultado).where(AsientoResultado.asiento_origen_id == origin_id)
    )
    db.execute(delete(AsientoResultado).where(AsientoResultado.id == origin_id))
    log_audit(
        db,
        user=user,
        table=record.__tablename__,
        record_id=origin_id,
        action=AuditAction.HARD_DELETE,
        changes={"asientos_eliminados": [str(entry.id) for entry in entries]},
    )
    db.commit()


@router.get(
    "/asientos", response_model=list[AsientoResultadoRead], dependencies=[Depends(require_enabled)]
)
def list_asientos(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    rubro_id: uuid.UUID | None = None,
    centro_id: uuid.UUID | None = None,
    busqueda: str | None = None,
    solo_origen: bool = False,
    solo_resultado: bool = False,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    statement = select(AsientoResultado).where(AsientoResultado.is_active.is_(True))
    if fecha_desde:
        statement = statement.where(AsientoResultado.fecha >= fecha_desde)
    if fecha_hasta:
        statement = statement.where(AsientoResultado.fecha <= fecha_hasta)
    if rubro_id:
        rubro_ids = {rubro_id}
        pending_ids = [rubro_id]
        while pending_ids:
            child_ids = list(
                db.scalars(
                    select(RubroResultado.id).where(RubroResultado.padre_id.in_(pending_ids))
                )
            )
            pending_ids = [item for item in child_ids if item not in rubro_ids]
            rubro_ids.update(pending_ids)
        statement = statement.where(AsientoResultado.rubro_id.in_(rubro_ids))
    if centro_id:
        statement = statement.where(AsientoResultado.centro_resultado_id == centro_id)
    if busqueda and busqueda.strip():
        value = f"%{busqueda.strip()}%"
        statement = statement.where(
            or_(
                AsientoResultado.descripcion.ilike(value),
                AsientoResultado.documento.ilike(value),
                AsientoResultado.observaciones.ilike(value),
            )
        )
    if solo_origen:
        statement = statement.where(AsientoResultado.asiento_origen_id.is_(None))
    if solo_resultado:
        statement = statement.where(AsientoResultado.es_resultado.is_(True))
    return list(
        db.scalars(
            statement.order_by(AsientoResultado.fecha.desc(), AsientoResultado.created_at.desc())
        )
    )


@router.get(
    "/ultimo-periodo",
    response_model=UltimoPeriodoResultadoRead,
    dependencies=[Depends(require_enabled)],
)
def latest_period(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    latest_date = db.scalar(
        select(func.max(AsientoResultado.fecha)).where(
            AsientoResultado.is_active.is_(True), AsientoResultado.es_resultado.is_(True)
        )
    )
    return UltimoPeriodoResultadoRead(
        periodo=latest_date.strftime("%Y-%m") if latest_date else None
    )


def signed_amount(entry: AsientoResultado) -> Decimal:
    # Credits increase income; debits increase costs and expenses, which reduce the result.
    return Decimal(entry.haber) - Decimal(entry.debe)


@router.get("/reporte.xlsx", dependencies=[Depends(require_enabled)])
def download_detailed_report(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    rubro_id: uuid.UUID | None = None,
    centro_id: uuid.UUID | None = None,
    origen: OrigenAsientoResultado | None = None,
    _: Annotated[User, Depends(require_admin)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_desde no puede ser posterior a fecha_hasta.",
        )
    filters = [
        AsientoResultado.is_active.is_(True),
        AsientoResultado.es_resultado.is_(True),
    ]
    if fecha_desde:
        filters.append(AsientoResultado.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(AsientoResultado.fecha <= fecha_hasta)
    if rubro_id:
        filters.append(AsientoResultado.rubro_id == rubro_id)
    if centro_id:
        filters.append(AsientoResultado.centro_resultado_id == centro_id)
    if origen:
        filters.append(AsientoResultado.origen == origen)
    statement = (
        select(AsientoResultado, RubroResultado, CentroResultado)
        .join(RubroResultado, AsientoResultado.rubro_id == RubroResultado.id)
        .outerjoin(CentroResultado, AsientoResultado.centro_resultado_id == CentroResultado.id)
        .where(*filters)
        .order_by(AsientoResultado.fecha, RubroResultado.codigo, AsientoResultado.created_at)
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Asientos EGyP"
    sheet.append(
        [
            "Fecha", "Periodo", "Codigo rubro", "Rubro", "Naturaleza", "Codigo centro",
            "Linea de negocio", "Descripcion", "Documento", "Moneda", "Debe", "Haber",
            "Resultado neto", "Origen", "Lote", "Fila origen", "Observaciones",
        ]
    )
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)
    for entry, rubro, centro in db.execute(statement):
        sheet.append(
            [
                entry.fecha, entry.fecha.strftime("%Y-%m"), rubro.codigo, rubro.nombre,
                rubro.naturaleza.value, centro.codigo if centro else "",
                centro.nombre if centro else "", entry.descripcion, entry.documento or "",
                entry.moneda, entry.debe, entry.haber, signed_amount(entry), entry.origen.value,
                str(entry.lote_id or ""), entry.numero_fila or "", entry.observaciones or "",
            ]
        )
    sheet.freeze_panes = "A2"
    widths = {
        "A": 13, "B": 11, "C": 16, "D": 28, "E": 20, "F": 16, "G": 24,
        "H": 36, "I": 18, "J": 10, "K": 14, "L": 14, "M": 16, "N": 15,
        "O": 38, "P": 12, "Q": 36,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    output = BytesIO()
    workbook.save(output)
    return StreamingResponse(
        BytesIO(output.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reporte_detallado_egyp.xlsx"'},
    )


@router.get(
    "/resumen", response_model=ResumenGananciasPerdidasRead, dependencies=[Depends(require_enabled)]
)
def summary(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_desde no puede ser posterior a fecha_hasta.",
        )
    all_centers = list(
        db.scalars(
            select(CentroResultado)
            .where(CentroResultado.is_active.is_(True))
            .order_by(CentroResultado.orden, CentroResultado.nombre)
        )
    )
    rubros = list(
        db.scalars(
            select(RubroResultado)
            .where(RubroResultado.is_active.is_(True))
            .order_by(RubroResultado.orden, RubroResultado.nombre)
        )
    )
    by_id = {rubro.id: rubro for rubro in rubros}
    totals = {
        rubro.id: {"total": ZERO, "centers": {center.codigo: ZERO for center in all_centers}}
        for rubro in rubros
    }
    total_by_nature = {nature: ZERO for nature in NaturalezaRubro}
    totals_by_center = {
        center.id: {nature: ZERO for nature in NaturalezaRubro}
        for center in all_centers
    }
    statement = select(AsientoResultado).where(
        AsientoResultado.is_active.is_(True), AsientoResultado.es_resultado.is_(True)
    )
    if fecha_desde:
        statement = statement.where(AsientoResultado.fecha >= fecha_desde)
    if fecha_hasta:
        statement = statement.where(AsientoResultado.fecha <= fecha_hasta)
    center_ids = {center.id: center.codigo for center in all_centers}
    used_center_ids: set[uuid.UUID] = set()
    for entry in db.scalars(statement):
        rubro = by_id.get(entry.rubro_id)
        if not rubro:
            continue
        amount = signed_amount(entry)
        total_by_nature[rubro.naturaleza] += amount
        if entry.centro_resultado_id in totals_by_center:
            totals_by_center[entry.centro_resultado_id][rubro.naturaleza] += amount
            used_center_ids.add(entry.centro_resultado_id)
        current: RubroResultado | None = rubro
        while current:
            totals[current.id]["total"] += amount
            if entry.centro_resultado_id in center_ids:
                totals[current.id]["centers"][center_ids[entry.centro_resultado_id]] += amount
            current = by_id.get(current.padre_id) if current.padre_id else None
    centers = [center for center in all_centers if center.id in used_center_ids]
    result_rows = [
        ResultadoRubroRead(
            rubro_id=rubro.id,
            codigo=rubro.codigo,
            nombre=rubro.nombre,
            naturaleza=rubro.naturaleza,
            padre_id=rubro.padre_id,
            total=totals[rubro.id]["total"],
            por_centro=totals[rubro.id]["centers"],
        )
        for rubro in rubros
    ]
    ingresos_brutos = total_by_nature[NaturalezaRubro.INGRESO]
    ingresos = (
        total_by_nature[NaturalezaRubro.INGRESO]
        + total_by_nature[NaturalezaRubro.INGRESO_FINANCIERO]
    )
    ingresos_netos = (
        total_by_nature[NaturalezaRubro.INGRESO] + total_by_nature[NaturalezaRubro.CONTRA_INGRESO]
    )
    utilidad_bruta = ingresos_netos + total_by_nature[NaturalezaRubro.COSTO_VENTA]
    gastos_operativos = total_by_nature[NaturalezaRubro.GASTO_OPERATIVO]
    utilidad_operativa = utilidad_bruta + gastos_operativos
    rentabilidad_por_centro = []
    for center in centers:
        values = totals_by_center[center.id]
        ingresos_netos_centro = values[NaturalezaRubro.INGRESO] + values[NaturalezaRubro.CONTRA_INGRESO]
        utilidad_bruta_centro = ingresos_netos_centro + values[NaturalezaRubro.COSTO_VENTA]
        utilidad_neta_centro = (
            values[NaturalezaRubro.INGRESO]
            + values[NaturalezaRubro.INGRESO_FINANCIERO]
            + values[NaturalezaRubro.CONTRA_INGRESO]
            + values[NaturalezaRubro.COSTO_VENTA]
            + values[NaturalezaRubro.GASTO_OPERATIVO]
            + values[NaturalezaRubro.GASTO_FINANCIERO]
            + values[NaturalezaRubro.IMPUESTO]
        )
        rentabilidad_por_centro.append(RentabilidadCentroResultadoRead(
            centro_id=center.id,
            codigo=center.codigo,
            nombre=center.nombre,
            ingresos_brutos=values[NaturalezaRubro.INGRESO],
            ingresos_netos=ingresos_netos_centro,
            utilidad_bruta=utilidad_bruta_centro,
            utilidad_neta=utilidad_neta_centro,
        ))
    return ResumenGananciasPerdidasRead(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        centros=centers,
        rubros=result_rows,
        ingresos_brutos=ingresos_brutos,
        ingresos_netos=ingresos_netos,
        utilidad_bruta=utilidad_bruta,
        gastos_operativos=gastos_operativos,
        utilidad_operativa=utilidad_operativa,
        utilidad_neta=ingresos
        + total_by_nature[NaturalezaRubro.CONTRA_INGRESO]
        + total_by_nature[NaturalezaRubro.COSTO_VENTA]
        + gastos_operativos
        + total_by_nature[NaturalezaRubro.GASTO_FINANCIERO]
        + total_by_nature[NaturalezaRubro.IMPUESTO],
        rentabilidad_por_centro=rentabilidad_por_centro,
    )
