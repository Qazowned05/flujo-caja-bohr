import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria
from app.modules.divisas.models import TipoCambio
from app.modules.flujo_caja.schemas import (
    DesgloseActividadRead,
    DesgloseConceptoRead,
    DesgloseTipoRead,
    FlujoCajaDesgloseTipificacionesRead,
    FlujoCajaResumenRead,
    ResumenCuentaRead,
    ResumenGrupoRead,
    SaldoFinalRead,
    SaldoPorFechaRead,
)
from app.modules.transacciones.models import OrigenTransaccion, Transaccion
from app.modules.usuarios.deps import get_current_user
from app.modules.usuarios.models import User

router = APIRouter(prefix="/flujo-caja", tags=["flujo-caja"])

ZERO = Decimal("0")


def empty_totals() -> dict[str, Decimal | int]:
    return {
        "ingresos_reales": ZERO,
        "egresos_reales": ZERO,
        "neto_real": ZERO,
        "ingresos_proyectados": ZERO,
        "egresos_proyectados": ZERO,
        "neto_proyectado": ZERO,
        "cantidad_reales": 0,
        "cantidad_proyectadas": 0,
    }


def add_transaction(totals: dict[str, Decimal | int], transaction: Transaccion) -> None:
    projected = transaction.origen == OrigenTransaccion.PROYECCION and not transaction.materializado
    income_key = "ingresos_proyectados" if projected else "ingresos_reales"
    expense_key = "egresos_proyectados" if projected else "egresos_reales"
    count_key = "cantidad_proyectadas" if projected else "cantidad_reales"
    net_key = "neto_proyectado" if projected else "neto_real"
    amount = Decimal(transaction.monto)
    totals[count_key] += 1  # type: ignore[operator]
    if amount > ZERO:
        totals[income_key] += amount  # type: ignore[operator]
    elif amount < ZERO:
        totals[expense_key] += -amount  # type: ignore[operator]
    totals[net_key] += amount  # type: ignore[operator]


def summary_values(
    totals: dict[str, Decimal | int], incluir_proyecciones: bool
) -> dict[str, Decimal | int]:
    return {
        **totals,
        "neto_total": totals["neto_real"]
        + (totals["neto_proyectado"] if incluir_proyecciones else ZERO),  # type: ignore[operator]
    }


@router.get("/resumen", response_model=FlujoCajaResumenRead)
def get_resumen(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    banco_id: uuid.UUID | None = None,
    cuenta_bancaria_id: uuid.UUID | None = None,
    actividad_id: uuid.UUID | None = None,
    moneda: str | None = Query(default=None, pattern=r"^[A-Za-z]{3}$"),
    incluir_proyecciones: bool = True,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FlujoCajaResumenRead:
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="fecha_desde no puede ser posterior a fecha_hasta.",
        )

    filters = [Transaccion.is_active.is_(True)]
    if fecha_desde:
        filters.append(Transaccion.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(Transaccion.fecha <= fecha_hasta)
    if banco_id:
        filters.append(CuentaBancaria.banco_id == banco_id)
    if cuenta_bancaria_id:
        filters.append(Transaccion.cuenta_bancaria_id == cuenta_bancaria_id)
    if actividad_id:
        filters.append(Transaccion.actividad_id == actividad_id)
    if moneda:
        filters.append(Transaccion.moneda == moneda.upper())
    if not incluir_proyecciones:
        filters.append(
            ~(
                (Transaccion.origen == OrigenTransaccion.PROYECCION)
                & Transaccion.materializado.is_(False)
            )
        )

    rows = db.execute(
        select(Transaccion, CuentaBancaria, Banco)
        .join(CuentaBancaria, Transaccion.cuenta_bancaria_id == CuentaBancaria.id)
        .join(Banco, CuentaBancaria.banco_id == Banco.id)
        .where(*filters)
    ).all()

    account_filters = []
    if banco_id:
        account_filters.append(CuentaBancaria.banco_id == banco_id)
    if cuenta_bancaria_id:
        account_filters.append(CuentaBancaria.id == cuenta_bancaria_id)
    if moneda:
        account_filters.append(CuentaBancaria.moneda == moneda.upper())
    accounts = list(db.scalars(select(CuentaBancaria).where(*account_filters)))
    balance_by_currency: dict[str, dict[str, Decimal]] = {}
    for account in accounts:
        balances = balance_by_currency.setdefault(
            account.moneda, {"saldo_real": ZERO, "saldo_final": ZERO}
        )
        initial = Decimal(account.saldo_inicial)
        balances["saldo_real"] += initial
        balances["saldo_final"] += initial

    balance_filters = [Transaccion.is_active.is_(True)]
    if fecha_hasta:
        balance_filters.append(Transaccion.fecha <= fecha_hasta)
    if banco_id:
        balance_filters.append(CuentaBancaria.banco_id == banco_id)
    if cuenta_bancaria_id:
        balance_filters.append(Transaccion.cuenta_bancaria_id == cuenta_bancaria_id)
    if actividad_id:
        balance_filters.append(Transaccion.actividad_id == actividad_id)
    if moneda:
        balance_filters.append(Transaccion.moneda == moneda.upper())
    balance_rows = db.execute(
        select(Transaccion, CuentaBancaria)
        .join(CuentaBancaria, Transaccion.cuenta_bancaria_id == CuentaBancaria.id)
        .where(*balance_filters)
    ).all()
    for transaction, account in balance_rows:
        balances = balance_by_currency.setdefault(
            account.moneda, {"saldo_real": ZERO, "saldo_final": ZERO}
        )
        amount = Decimal(transaction.monto)
        projected = (
            transaction.origen == OrigenTransaccion.PROYECCION and not transaction.materializado
        )
        if projected:
            if incluir_proyecciones:
                balances["saldo_final"] += amount
        else:
            balances["saldo_real"] += amount
            balances["saldo_final"] += amount

    by_currency: dict[str, dict[str, Decimal | int]] = {}
    by_account: dict[tuple[uuid.UUID, str], dict[str, object]] = {}
    for transaction, account, bank in rows:
        currency_totals = by_currency.setdefault(transaction.moneda, empty_totals())
        add_transaction(currency_totals, transaction)

        account_key = (account.id, transaction.moneda)
        account_group = by_account.setdefault(
            account_key,
            {
                "cuenta_bancaria_id": account.id,
                "cuenta_alias": account.alias,
                "banco_id": bank.id,
                "banco_nombre": bank.nombre,
                "moneda": transaction.moneda,
                "totals": empty_totals(),
            },
        )
        add_transaction(account_group["totals"], transaction)  # type: ignore[arg-type]

    por_divisa = [
        ResumenGrupoRead(moneda=currency, **summary_values(totals, incluir_proyecciones))
        for currency, totals in sorted(by_currency.items())
    ]
    por_cuenta = [
        ResumenCuentaRead(
            cuenta_bancaria_id=group["cuenta_bancaria_id"],
            cuenta_alias=group["cuenta_alias"],
            banco_id=group["banco_id"],
            banco_nombre=group["banco_nombre"],
            moneda=group["moneda"],
            **summary_values(group["totals"], incluir_proyecciones),  # type: ignore[arg-type]
        )
        for group in sorted(
            by_account.values(),
            key=lambda item: (item["moneda"], item["banco_nombre"], item["cuenta_alias"]),
        )
    ]
    return FlujoCajaResumenRead(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        incluir_proyecciones=incluir_proyecciones,
        por_divisa=por_divisa,
        por_cuenta=por_cuenta,
        saldos_finales=[
            SaldoFinalRead(moneda=currency, **balances)
            for currency, balances in sorted(balance_by_currency.items())
        ],
    )


def add_amount(group: dict[str, object], transaction_date: date, amount: Decimal) -> None:
    group["total"] = Decimal(group["total"]) + amount
    values = group["valores_por_fecha"]
    assert isinstance(values, dict)
    key = transaction_date.isoformat()
    values[key] = Decimal(values.get(key, ZERO)) + amount


@router.get("/desglose-tipificaciones", response_model=FlujoCajaDesgloseTipificacionesRead)
def get_desglose_tipificaciones(
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    cuenta_bancaria_id: uuid.UUID | None = None,
    actividad_id: uuid.UUID | None = None,
    moneda_visualizacion: str = Query(default="PEN", pattern=r"^[A-Za-z]{3}$"),
    incluir_proyecciones: bool = True,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
) -> FlujoCajaDesgloseTipificacionesRead:
    today = date.today()
    fecha_desde = fecha_desde or today.replace(day=1)
    fecha_hasta = fecha_hasta or today
    if fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=422, detail="fecha_desde no puede ser posterior a fecha_hasta."
        )
    if (fecha_hasta - fecha_desde).days > 93:
        raise HTTPException(status_code=422, detail="El rango maximo es de 93 dias.")

    currency = moneda_visualizacion.upper()
    filters = [
        Transaccion.is_active.is_(True),
        Transaccion.fecha <= fecha_hasta,
    ]
    if cuenta_bancaria_id:
        filters.append(Transaccion.cuenta_bancaria_id == cuenta_bancaria_id)
    if actividad_id:
        filters.append(Transaccion.actividad_id == actividad_id)
    if not incluir_proyecciones:
        filters.append(
            ~(
                (Transaccion.origen == OrigenTransaccion.PROYECCION)
                & Transaccion.materializado.is_(False)
            )
        )
    accounts_statement = select(CuentaBancaria)
    if cuenta_bancaria_id:
        accounts_statement = accounts_statement.where(CuentaBancaria.id == cuenta_bancaria_id)
    accounts = list(db.scalars(accounts_statement))
    account_ids = [account.id for account in accounts]

    rows = db.execute(
        select(Transaccion, Actividad, Concepto, Tipo)
        .outerjoin(Actividad, Transaccion.actividad_id == Actividad.id)
        .outerjoin(Concepto, Transaccion.concepto_id == Concepto.id)
        .outerjoin(Tipo, Transaccion.tipo_id == Tipo.id)
        .where(*filters, Transaccion.cuenta_bancaria_id.in_(account_ids))
    ).all()

    rates: dict[tuple[str, str], Decimal] = {}
    for rate in db.scalars(
        select(TipoCambio)
        .where(TipoCambio.is_active.is_(True))
        .order_by(TipoCambio.fecha_vigencia.desc(), TipoCambio.created_at.desc())
    ):
        rates.setdefault((rate.moneda_origen, rate.moneda_destino), Decimal(rate.tasa))

    activities: dict[uuid.UUID | None, dict[str, object]] = {}
    missing_rate = 0
    movement_count = 0
    daily_movements = {
        (fecha_desde + timedelta(days=offset)).isoformat(): ZERO
        for offset in range((fecha_hasta - fecha_desde).days + 1)
    }

    def convert_amount(amount: Decimal, source_currency: str) -> Decimal | None:
        nonlocal missing_rate
        if source_currency == currency:
            return amount
        direct = rates.get((source_currency, currency))
        inverse = rates.get((currency, source_currency))
        if direct is not None:
            return amount * direct
        if inverse is not None and inverse != ZERO:
            return amount / inverse
        missing_rate += 1
        return None

    opening_balance = ZERO
    for account in accounts:
        amount = convert_amount(Decimal(account.saldo_inicial), account.moneda)
        if amount is not None:
            opening_balance += amount

    for transaction, activity, concept, kind in rows:
        amount = convert_amount(Decimal(transaction.monto), transaction.moneda)
        if amount is None:
            continue
        if transaction.fecha < fecha_desde:
            opening_balance += amount
            continue

        date_key = transaction.fecha.isoformat()
        daily_movements[date_key] += amount
        movement_count += 1
        if activity is None or concept is None or kind is None:
            untyped_group = activities.setdefault(
                None,
                {
                    "id": None,
                    "nombre": "Sin tipificar",
                    "orden": 0,
                    "total": ZERO,
                    "valores_por_fecha": {},
                    "conceptos": {},
                },
            )
            add_amount(untyped_group, transaction.fecha, amount)
            continue

        activity_id, activity_name = activity.id, activity.nombre
        concept_id, concept_name = concept.id, concept.nombre
        kind_id, kind_name = kind.id, kind.nombre

        activity_group = activities.setdefault(
            activity_id,
            {
                "id": activity_id,
                "nombre": activity_name,
                "orden": activity.orden,
                "total": ZERO,
                "valores_por_fecha": {},
                "conceptos": {},
            },
        )
        concepts = activity_group["conceptos"]
        assert isinstance(concepts, dict)
        concept_group = concepts.setdefault(
            concept_id,
            {
                "id": concept_id,
                "nombre": concept_name,
                "incluye_flujo_bruto_operativo": concept.incluye_flujo_bruto_operativo,
                "incluye_flujo_neto_operativo": concept.incluye_flujo_neto_operativo,
                "total": ZERO,
                "valores_por_fecha": {},
                "tipos": {},
            },
        )
        kinds = concept_group["tipos"]
        assert isinstance(kinds, dict)
        kind_group = kinds.setdefault(
            kind_id,
            {"id": kind_id, "nombre": kind_name, "total": ZERO, "valores_por_fecha": {}},
        )
        add_amount(activity_group, transaction.fecha, amount)
        add_amount(concept_group, transaction.fecha, amount)
        add_amount(kind_group, transaction.fecha, amount)

    activity_output = []
    for activity in activities.values():
        concept_output = []
        for concept in activity["conceptos"].values():
            kind_output = [DesgloseTipoRead(**kind) for kind in concept["tipos"].values()]
            kind_output.sort(key=lambda item: item.nombre.casefold())
            concept_output.append(DesgloseConceptoRead(**(concept | {"tipos": kind_output})))
        concept_output.sort(key=lambda item: item.nombre.casefold())
        activity_output.append(DesgloseActividadRead(**(activity | {"conceptos": concept_output})))
    activity_output.sort(key=lambda item: (item.orden, item.nombre.casefold()))
    saldos_por_fecha: dict[str, SaldoPorFechaRead] = {}
    current_balance = opening_balance
    for date_key, daily_total in daily_movements.items():
        saldos_por_fecha[date_key] = SaldoPorFechaRead(
            saldo_inicial=current_balance,
            saldo_final=current_balance + daily_total,
        )
        current_balance += daily_total
    return FlujoCajaDesgloseTipificacionesRead(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        fechas=[
            fecha_desde + timedelta(days=offset)
            for offset in range((fecha_hasta - fecha_desde).days + 1)
        ],
        moneda_visualizacion=currency,
        actividades=activity_output,
        saldos_por_fecha=saldos_por_fecha,
        movimientos_diarios_por_fecha=daily_movements,
        cantidad_movimientos=movement_count,
        cantidad_sin_tasa=missing_rate,
    )
