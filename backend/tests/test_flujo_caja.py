import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria
from app.modules.divisas.models import TipoCambio
from app.modules.shared.models import AuditAction, AuditLog
from app.modules.transacciones.models import EstadoTransaccion, OrigenTransaccion, Transaccion
from app.modules.usuarios.deps import get_current_user
from app.modules.usuarios.models import User, UserRole


@pytest.fixture()
def client_and_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = User(
        email="asesor@example.com",
        hashed_password="unused",
        nombre="Asesor",
        rol=UserRole.ASESOR,
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, session, user
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def make_account(
    session: Session, name: str, currency: str, saldo_inicial: str = "0"
) -> tuple[Banco, CuentaBancaria]:
    bank = Banco(nombre=name, codigo=f"{name}-{uuid.uuid4()}")
    session.add(bank)
    session.flush()
    account = CuentaBancaria(
        banco_id=bank.id,
        alias=f"Cuenta {name}",
        numero_cuenta=str(uuid.uuid4()),
        moneda=currency,
        saldo_inicial=Decimal(saldo_inicial),
    )
    session.add(account)
    session.commit()
    return bank, account


def make_transaction(
    session: Session, user: User, account: CuentaBancaria, amount: str, **values
) -> Transaccion:
    transaction = Transaccion(
        **{
            "fecha": date(2026, 8, 10),
            "descripcion": "Movimiento",
            "n_operacion": f"OP-{uuid.uuid4()}",
            "monto": Decimal(amount),
            "moneda": account.moneda,
            "cuenta_bancaria_id": account.id,
            "origen": OrigenTransaccion.IMPORTADO,
            "estado": EstadoTransaccion.PENDIENTE_TIPIFICAR,
            "created_by_id": user.id,
            "updated_by_id": user.id,
        }
        | values,
    )
    session.add(transaction)
    session.commit()
    return transaction


def test_resumen_separates_currencies_and_classifies_movements(client_and_session):
    client, session, user = client_and_session
    _, pen_account = make_account(session, "Banco PEN", "PEN")
    _, usd_account = make_account(session, "Banco USD", "USD")
    make_transaction(session, user, pen_account, "100.00")
    make_transaction(session, user, pen_account, "-30.00")
    make_transaction(
        session,
        user,
        pen_account,
        "50.00",
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )
    make_transaction(
        session,
        user,
        pen_account,
        "20.00",
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.CONFIRMADO,
        materializado=True,
    )
    make_transaction(session, user, usd_account, "10.00")

    response = client.get("/api/v1/flujo-caja/resumen")

    assert response.status_code == 200
    groups = {group["moneda"]: group for group in response.json()["por_divisa"]}
    assert set(groups) == {"PEN", "USD"}
    assert groups["PEN"] == {
        "moneda": "PEN",
        "ingresos_reales": "120.00",
        "egresos_reales": "30.00",
        "neto_real": "90.00",
        "ingresos_proyectados": "50.00",
        "egresos_proyectados": "0",
        "neto_proyectado": "50.00",
        "neto_total": "140.00",
        "cantidad_reales": 3,
        "cantidad_proyectadas": 1,
    }
    assert groups["USD"]["neto_total"] == "10.00"
    balances = {item["moneda"]: item for item in response.json()["saldos_finales"]}
    assert balances["PEN"] == {"moneda": "PEN", "saldo_real": "90.00", "saldo_final": "140.00"}
    assert balances["USD"] == {"moneda": "USD", "saldo_real": "10.00", "saldo_final": "10.00"}

def test_resumen_filters_and_excludes_projections(client_and_session):
    client, session, user = client_and_session
    pen_bank, pen_account = make_account(session, "Banco PEN", "PEN")
    _, usd_account = make_account(session, "Banco USD", "USD")
    pen_account.is_active = False
    session.commit()
    make_transaction(session, user, pen_account, "100.00", fecha=date(2026, 8, 10))
    make_transaction(
        session,
        user,
        pen_account,
        "25.00",
        fecha=date(2026, 8, 11),
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )
    make_transaction(session, user, usd_account, "50.00", fecha=date(2026, 8, 10))

    response = client.get(
        "/api/v1/flujo-caja/resumen",
        params={
            "banco_id": str(pen_bank.id),
            "cuenta_bancaria_id": str(pen_account.id),
            "moneda": "pen",
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-10",
            "incluir_proyecciones": "false",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["incluir_proyecciones"] is False
    assert body["por_divisa"][0]["neto_total"] == "100.00"
    assert body["por_divisa"][0]["cantidad_proyectadas"] == 0
    assert body["por_cuenta"][0]["cuenta_bancaria_id"] == str(pen_account.id)

    invalid = client.get(
        "/api/v1/flujo-caja/resumen",
        params={"fecha_desde": "2026-08-11", "fecha_hasta": "2026-08-10"},
    )
    assert invalid.status_code == 422


def test_desglose_converts_groups_and_filters_projections(client_and_session):
    client, session, user = client_and_session
    _, pen_account = make_account(session, "Banco PEN", "PEN")
    _, usd_account = make_account(session, "Banco USD", "USD")
    activity = Actividad(nombre="Ventas", orden=3)
    session.add(activity)
    session.flush()
    concept = Concepto(
        actividad_id=activity.id,
        nombre="Cobros",
        incluye_flujo_bruto_operativo=True,
        incluye_flujo_neto_operativo=True,
    )
    session.add(concept)
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Contado")
    session.add(kind)
    session.flush()
    session.add_all(
        [
            TipoCambio(
                moneda_origen="USD",
                moneda_destino="PEN",
                tasa=Decimal("4"),
                fecha_vigencia=date(2026, 8, 1),
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
            TipoCambio(
                moneda_origen="PEN",
                moneda_destino="EUR",
                tasa=Decimal("5"),
                fecha_vigencia=date(2026, 8, 1),
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
        ]
    )
    session.commit()
    typed = {"actividad_id": activity.id, "concepto_id": concept.id, "tipo_id": kind.id}
    make_transaction(session, user, usd_account, "10", **typed)
    make_transaction(
        session,
        user,
        pen_account,
        "20",
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
        **typed,
    )
    make_transaction(session, user, pen_account, "5")

    response = client.get(
        "/api/v1/flujo-caja/desglose-tipificaciones",
        params={
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-10",
            "moneda_visualizacion": "PEN",
            "incluir_proyecciones": "false",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cantidad_movimientos"] == 2
    assert body["cantidad_sin_tasa"] == 0
    groups = {item["nombre"]: item for item in body["actividades"]}
    assert groups["Ventas"]["orden"] == 3
    assert Decimal(groups["Ventas"]["total"]) == Decimal("40.00")
    assert Decimal(groups["Ventas"]["conceptos"][0]["tipos"][0]["total"]) == Decimal("40.00")
    assert groups["Ventas"]["conceptos"][0]["incluye_flujo_bruto_operativo"] is True
    assert groups["Ventas"]["conceptos"][0]["incluye_flujo_neto_operativo"] is True
    assert Decimal(groups["Sin tipificar"]["total"]) == Decimal("5.00")
    assert Decimal(body["movimientos_diarios_por_fecha"]["2026-08-10"]) == Decimal("45.00")
    assert Decimal(body["saldos_por_fecha"]["2026-08-10"]["saldo_final"]) == Decimal("45.00")

    with_projections = client.get(
        "/api/v1/flujo-caja/desglose-tipificaciones",
        params={
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-10",
            "moneda_visualizacion": "PEN",
            "incluir_proyecciones": "true",
        },
    )
    projected_groups = {item["nombre"]: item for item in with_projections.json()["actividades"]}
    assert Decimal(projected_groups["Ventas"]["total"]) == Decimal("60.00")


def test_desglose_uses_inverse_rate_and_validates_range(client_and_session):
    client, session, user = client_and_session
    _, pen_account = make_account(session, "Banco PEN", "PEN")
    session.add(
        TipoCambio(
            moneda_origen="USD",
            moneda_destino="PEN",
            tasa=Decimal("4"),
            fecha_vigencia=date(2026, 8, 1),
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    session.commit()
    make_transaction(session, user, pen_account, "20")

    response = client.get(
        "/api/v1/flujo-caja/desglose-tipificaciones",
        params={
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-10",
            "moneda_visualizacion": "USD",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["actividades"][0]["total"]) == Decimal("5.00")
    assert body["actividades"][0]["nombre"] == "Sin tipificar"
    assert Decimal(body["saldos_por_fecha"]["2026-08-10"]["saldo_final"]) == Decimal("5.00")
    assert (
        client.get(
            "/api/v1/flujo-caja/desglose-tipificaciones",
            params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-05-01"},
        ).status_code
        == 422
    )


def test_desglose_daily_balances_include_opening_movements_and_account_filter(client_and_session):
    client, session, user = client_and_session
    _, pen_account = make_account(session, "Banco PEN", "PEN", saldo_inicial="100")
    _, usd_account = make_account(session, "Banco USD", "USD", saldo_inicial="10")
    session.add(
        TipoCambio(
            moneda_origen="USD",
            moneda_destino="PEN",
            tasa=Decimal("4"),
            fecha_vigencia=date(2026, 8, 1),
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    session.commit()
    make_transaction(session, user, pen_account, "25", fecha=date(2026, 8, 9))
    make_transaction(session, user, pen_account, "-10", fecha=date(2026, 8, 10))
    make_transaction(
        session,
        user,
        pen_account,
        "100",
        fecha=date(2026, 8, 10),
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )
    make_transaction(session, user, usd_account, "5", fecha=date(2026, 8, 10))
    make_transaction(session, user, pen_account, "-15", fecha=date(2026, 8, 11))

    response = client.get(
        "/api/v1/flujo-caja/desglose-tipificaciones",
        params={
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-11",
            "moneda_visualizacion": "PEN",
            "incluir_proyecciones": "false",
        },
    )

    assert response.status_code == 200
    balances = response.json()["saldos_por_fecha"]
    assert Decimal(balances["2026-08-10"]["saldo_inicial"]) == Decimal("165.00")
    assert Decimal(balances["2026-08-10"]["saldo_final"]) == Decimal("175.00")
    assert Decimal(balances["2026-08-11"]["saldo_inicial"]) == Decimal("175.00")
    assert Decimal(balances["2026-08-11"]["saldo_final"]) == Decimal("160.00")

    filtered = client.get(
        "/api/v1/flujo-caja/desglose-tipificaciones",
        params={
            "fecha_desde": "2026-08-10",
            "fecha_hasta": "2026-08-11",
            "cuenta_bancaria_id": str(pen_account.id),
            "moneda_visualizacion": "PEN",
            "incluir_proyecciones": "false",
        },
    )

    assert filtered.status_code == 200
    balances = filtered.json()["saldos_por_fecha"]
    assert Decimal(balances["2026-08-10"]["saldo_inicial"]) == Decimal("125.00")
    assert Decimal(balances["2026-08-10"]["saldo_final"]) == Decimal("115.00")
    assert Decimal(balances["2026-08-11"]["saldo_inicial"]) == Decimal("115.00")
    assert Decimal(balances["2026-08-11"]["saldo_final"]) == Decimal("100.00")


def test_cuenta_bancaria_persists_normalized_initial_balance_and_audits(client_and_session):
    client, session, _ = client_and_session
    bank = Banco(nombre="Banco", codigo="BANCO")
    session.add(bank)
    session.commit()

    created = client.post(
        "/api/v1/cuentas-bancarias",
        json={
            "banco_id": str(bank.id),
            "alias": "Principal",
            "numero_cuenta": "001",
            "moneda": "PEN",
            "saldo_inicial": "12.345",
        },
    )

    assert created.status_code == 201
    assert created.json()["saldo_inicial"] == "12.35"
    account_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/cuentas-bancarias/{account_id}", json={"saldo_inicial": "-3.2"}
    )

    assert updated.status_code == 200
    assert updated.json()["saldo_inicial"] == "-3.20"
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == uuid.UUID(account_id), AuditLog.accion == AuditAction.UPDATE
        )
    )
    assert audit is not None
    assert audit.cambios["saldo_inicial"] == {"old": 12.35, "new": -3.2}
