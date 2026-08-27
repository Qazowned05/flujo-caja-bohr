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
from app.modules.shared.models import AuditAction, AuditLog
from app.modules.sucursales.models import Sucursal
from app.modules.transacciones.models import EstadoTransaccion, OrigenTransaccion, Transaccion
from app.modules.usuarios.deps import get_current_user
from app.modules.usuarios.models import User, UserRole
from app.modules.vendedores.models import Vendedor


@pytest.fixture()
def client_and_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = User(
        id=uuid.uuid4(),
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


def make_transaction(
    session: Session, user: User, account: CuentaBancaria, **values
) -> Transaccion:
    transaction_values = {
        "fecha": date(2026, 8, 1),
        "descripcion": "Movimiento",
        "n_operacion": f"OP-{uuid.uuid4()}",
        "monto": Decimal("10.00"),
        "moneda": account.moneda,
        "cuenta_bancaria_id": account.id,
        "origen": OrigenTransaccion.IMPORTADO,
        "estado": EstadoTransaccion.PENDIENTE_TIPIFICAR,
        "created_by_id": user.id,
        "updated_by_id": user.id,
    }
    transaction = Transaccion(**(transaction_values | values))
    session.add(transaction)
    session.commit()
    return transaction


def make_account(session: Session, moneda: str = "PEN") -> CuentaBancaria:
    bank = Banco(nombre=f"Banco {uuid.uuid4()}", codigo=f"BANCO-{uuid.uuid4()}")
    session.add(bank)
    session.flush()
    account = CuentaBancaria(
        banco_id=bank.id,
        alias="Principal",
        numero_cuenta=str(uuid.uuid4()),
        moneda=moneda,
    )
    session.add(account)
    session.commit()
    return account


def test_list_transacciones_filters_by_creator_and_includes_name(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    other_user = User(
        email="otro@example.com",
        hashed_password="unused",
        nombre="Otro Asesor",
        rol=UserRole.ASESOR,
        is_active=True,
        is_superuser=False,
    )
    session.add(other_user)
    session.commit()
    make_transaction(session, user, account, descripcion="Registro propio")
    make_transaction(session, other_user, account, descripcion="Registro ajeno")

    response = client.get(
        "/api/v1/transacciones", params={"created_by_id": str(other_user.id)}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["descripcion"] == "Registro ajeno"
    assert body["items"][0]["created_by"] == {
        "id": str(other_user.id),
        "nombre": "Otro Asesor",
    }
    assert body["items"][0]["updated_by"] == {
        "id": str(other_user.id),
        "nombre": "Otro Asesor",
    }


def test_list_transacciones_searches_operation_or_description(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    make_transaction(session, user, account, n_operacion="COB-001", descripcion="Cobro de factura")
    make_transaction(session, user, account, n_operacion="PAG-002", descripcion="Pago a proveedor")

    by_operation = client.get("/api/v1/transacciones", params={"busqueda": "COB-001"})
    by_description = client.get("/api/v1/transacciones", params={"busqueda": "proveedor"})

    assert by_operation.status_code == 200
    assert [item["n_operacion"] for item in by_operation.json()["items"]] == ["COB-001"]
    assert by_description.status_code == 200
    assert [item["n_operacion"] for item in by_description.json()["items"]] == ["PAG-002"]


def test_list_transacciones_filters_by_document_presence(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    make_transaction(session, user, account, descripcion="Con documento", documento="FAC-001")
    make_transaction(session, user, account, descripcion="Sin documento", documento=None)
    make_transaction(session, user, account, descripcion="Documento vacio", documento="  ")

    with_document = client.get("/api/v1/transacciones", params={"con_documento": "true"})
    without_document = client.get("/api/v1/transacciones", params={"con_documento": "false"})

    assert [item["descripcion"] for item in with_document.json()["items"]] == ["Con documento"]
    assert {item["descripcion"] for item in without_document.json()["items"]} == {
        "Sin documento",
        "Documento vacio",
    }


def test_multiple_transaction_creates_searches_and_updates_operations(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    payload = {
        "fecha": "2026-08-10",
        "descripcion": "Cobranza agrupada",
        "monto": "70.00",
        "cuenta_bancaria_id": str(account.id),
        "operaciones": ["VOUCHER-37", "VOUCHER-25", "VOUCHER-08"],
    }

    created = client.post("/api/v1/transacciones/multiple", json=payload)

    assert created.status_code == 201
    body = created.json()
    assert body["origen"] == "MULTIPLE"
    assert body["n_operacion"] is None
    assert body["numeros_operacion"] == payload["operaciones"]
    searched = client.get("/api/v1/transacciones", params={"busqueda": "VOUCHER-25"})
    assert [item["id"] for item in searched.json()["items"]] == [body["id"]]

    updated = client.patch(
        f"/api/v1/transacciones/{body['id']}/operaciones",
        json={"operaciones": ["VOUCHER-37", "VOUCHER-25", "VOUCHER-08", "VOUCHER-10"]},
    )
    assert updated.status_code == 200
    assert updated.json()["numeros_operacion"][-1] == "VOUCHER-10"
    duplicate = client.post(
        "/api/v1/transacciones/multiple",
        json={**payload, "operaciones": ["VOUCHER-25", "OTRO"]},
    )
    assert duplicate.status_code == 409


def test_create_proyeccion_inherits_currency_status_and_audits(client_and_session):
    client, session, _ = client_and_session
    account = make_account(session, moneda="USD")
    activity = Actividad(nombre="Actividad proyeccion")
    session.add(activity)
    session.flush()
    concept = Concepto(actividad_id=activity.id, nombre="Concepto proyeccion")
    session.add(concept)
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Tipo proyeccion")
    session.add(kind)
    session.commit()

    response = client.post(
        "/api/v1/transacciones/proyeccion",
        json={
            "fecha": "2026-08-10",
            "descripcion": "Cobro proyectado",
            "monto": "125.50",
            "cuenta_bancaria_id": str(account.id),
            "actividad_id": str(activity.id),
            "concepto_id": str(concept.id),
            "tipo_id": str(kind.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["moneda"] == "USD"
    assert body["origen"] == "PROYECCION"
    assert body["estado"] == "PROYECTADO"
    assert body["materializado"] is False
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == uuid.UUID(body["id"]),
            AuditLog.accion == AuditAction.CREATE,
        )
    )
    assert audit is not None


def test_create_manual_validates_categories_and_inherits_account_currency(client_and_session):
    client, session, user = client_and_session
    account = make_account(session, moneda="USD")
    missing_operation = client.post(
        "/api/v1/transacciones/manual",
        json={
            "fecha": "2026-08-10",
            "descripcion": "Cobro sin operación",
            "monto": "125.50",
            "cuenta_bancaria_id": str(account.id),
        },
    )
    assert missing_operation.status_code == 422

    activity = Actividad(nombre="Ventas")
    session.add(activity)
    session.flush()
    concept = Concepto(actividad_id=activity.id, nombre="Cobros")
    session.add(concept)
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Contado")
    session.add(kind)
    session.commit()

    response = client.post(
        "/api/v1/transacciones/manual",
        json={
            "fecha": "2026-08-10",
            "descripcion": "Cobro manual",
            "n_operacion": "MAN-001",
            "monto": "125.50",
            "cuenta_bancaria_id": str(account.id),
            "actividad_id": str(activity.id),
            "concepto_id": str(concept.id),
            "tipo_id": str(kind.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["moneda"] == "USD"
    assert body["origen"] == "MANUAL"
    assert body["estado"] == "TIPIFICADO"
    assert body["materializado"] is False
    assert (
        session.scalar(
            select(AuditLog).where(
                AuditLog.registro_id == uuid.UUID(body["id"]), AuditLog.accion == AuditAction.CREATE
            )
        )
        is not None
    )
    duplicate = client.post(
        "/api/v1/transacciones/manual",
        json={
            "fecha": "2026-08-10",
            "descripcion": "Duplicado",
            "n_operacion": "MAN-001",
            "monto": "1",
            "cuenta_bancaria_id": str(account.id),
        },
    )
    assert duplicate.status_code == 409


def test_materializar_proyeccion_updates_state_and_audits(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    transaction = make_transaction(
        session,
        user,
        account,
        n_operacion=None,
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )

    response = client.patch(
        f"/api/v1/transacciones/{transaction.id}/materializar",
        json={"n_operacion": "OP-REAL", "descripcion": "Cobro confirmado"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["n_operacion"] == "OP-REAL"
    assert body["origen"] == "MANUAL"
    assert body["estado"] == "CONFIRMADO"
    assert body["materializado"] is True
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == transaction.id,
            AuditLog.accion == AuditAction.UPDATE,
        )
    )
    assert audit is not None
    assert {"n_operacion", "origen", "estado", "materializado"} <= set(audit.cambios)


def test_materializar_rejects_duplicate_and_non_projection(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    make_transaction(session, user, account, n_operacion="OP-DUPLICADA")
    projection = make_transaction(
        session,
        user,
        account,
        n_operacion=None,
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )

    duplicate = client.patch(
        f"/api/v1/transacciones/{projection.id}/materializar",
        json={"n_operacion": "OP-DUPLICADA"},
    )
    assert duplicate.status_code == 409

    imported = make_transaction(session, user, account)
    non_projection = client.patch(
        f"/api/v1/transacciones/{imported.id}/materializar",
        json={"n_operacion": "OP-NUEVA"},
    )
    assert non_projection.status_code == 409


def test_update_real_transaction_associates_and_hides_pending_projection(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    real = make_transaction(session, user, account, n_operacion="OP-REAL")
    projection = make_transaction(
        session,
        user,
        account,
        n_operacion=None,
        origen=OrigenTransaccion.PROYECCION,
        estado=EstadoTransaccion.PROYECTADO,
        materializado=False,
    )

    response = client.patch(
        f"/api/v1/transacciones/{real.id}", json={"proyeccion_id": str(projection.id)}
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(real.id)
    session.refresh(projection)
    assert projection.is_active is False
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == projection.id,
            AuditLog.accion == AuditAction.SOFT_DELETE,
        )
    )
    assert audit is not None
    assert audit.cambios["movimiento_real_id"] == str(real.id)


def test_valid_typification_sets_status_and_audits(client_and_session):
    client, session, user = client_and_session
    bank = Banco(nombre="Banco", codigo="BANCO")
    activity = Actividad(nombre="Ventas")
    session.add_all([bank, activity])
    session.flush()
    account = CuentaBancaria(banco_id=bank.id, alias="Principal", numero_cuenta="123", moneda="PEN")
    concept = Concepto(actividad_id=activity.id, nombre="Cobros")
    session.add_all([account, concept])
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Contado")
    session.add(kind)
    session.commit()
    transaction = make_transaction(session, user, account)

    response = client.patch(
        f"/api/v1/transacciones/{transaction.id}",
        json={
            "actividad_id": str(activity.id),
            "concepto_id": str(concept.id),
            "tipo_id": str(kind.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "TIPIFICADO"
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.tabla == "transacciones",
            AuditLog.registro_id == transaction.id,
            AuditLog.accion == AuditAction.UPDATE,
        )
    )
    assert audit is not None
    assert set(audit.cambios) == {"actividad_id", "concepto_id", "tipo_id", "estado"}
    assert audit.cambios["estado"]["new"] == "TIPIFICADO"


def test_invalid_typification_hierarchy_returns_422_without_changes(client_and_session):
    client, session, user = client_and_session
    bank = Banco(nombre="Banco", codigo="BANCO")
    activity = Actividad(nombre="Ventas")
    other_activity = Actividad(nombre="Compras")
    session.add_all([bank, activity, other_activity])
    session.flush()
    account = CuentaBancaria(banco_id=bank.id, alias="Principal", numero_cuenta="123", moneda="PEN")
    concept = Concepto(actividad_id=activity.id, nombre="Cobros")
    session.add_all([account, concept])
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Contado")
    session.add(kind)
    session.commit()
    transaction = make_transaction(session, user, account)

    response = client.patch(
        f"/api/v1/transacciones/{transaction.id}",
        json={
            "actividad_id": str(other_activity.id),
            "concepto_id": str(concept.id),
            "tipo_id": str(kind.id),
        },
    )

    assert response.status_code == 422
    session.refresh(transaction)
    assert transaction.actividad_id is None
    assert transaction.concepto_id is None
    assert transaction.tipo_id is None
    assert transaction.estado == EstadoTransaccion.PENDIENTE_TIPIFICAR
    assert session.scalar(select(AuditLog).where(AuditLog.registro_id == transaction.id)) is None


def test_list_filters_and_pagination(client_and_session):
    client, session, user = client_and_session
    bank_a = Banco(nombre="Banco A", codigo="BANCO-A")
    bank_b = Banco(nombre="Banco B", codigo="BANCO-B")
    branch = Sucursal(nombre="Centro", codigo="CENTRO")
    session.add_all([bank_a, bank_b, branch])
    session.flush()
    seller = Vendedor(nombre="Ana", codigo="ANA", sucursal_id=branch.id)
    account_a = CuentaBancaria(banco_id=bank_a.id, alias="A", numero_cuenta="111", moneda="PEN")
    account_b = CuentaBancaria(banco_id=bank_b.id, alias="B", numero_cuenta="222", moneda="USD")
    session.add_all([seller, account_a, account_b])
    session.commit()
    first = make_transaction(
        session,
        user,
        account_a,
        fecha=date(2026, 8, 2),
        vendedor_id=seller.id,
        sucursal_id=branch.id,
        estado=EstadoTransaccion.TIPIFICADO,
    )
    second = make_transaction(
        session,
        user,
        account_a,
        fecha=date(2026, 8, 1),
        vendedor_id=seller.id,
        sucursal_id=branch.id,
    )
    make_transaction(session, user, account_b, fecha=date(2026, 7, 1))

    response = client.get(
        "/api/v1/transacciones",
        params={
            "banco_id": str(bank_a.id),
            "cuenta_bancaria_id": str(account_a.id),
            "moneda": "pen",
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2026-08-02",
            "estado": "TIPIFICADO",
            "vendedor_id": str(seller.id),
            "sucursal_id": str(branch.id),
            "limit": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(first.id)

    page = client.get(
        "/api/v1/transacciones",
        params={"banco_id": str(bank_a.id), "offset": 1, "limit": 1},
    )
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["items"][0]["id"] == str(second.id)


def test_list_filters_combined_typification_hierarchy_and_dates(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    activity = Actividad(nombre="Inversion")
    other_activity = Actividad(nombre="Operacion")
    session.add_all([activity, other_activity])
    session.flush()
    concept = Concepto(actividad_id=activity.id, nombre="Costos directos")
    other_concept = Concepto(actividad_id=activity.id, nombre="Otros costos")
    session.add_all([concept, other_concept])
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Recargas")
    other_kind = Tipo(concepto_id=other_concept.id, nombre="Servicios")
    session.add_all([kind, other_kind])
    session.commit()
    expected = make_transaction(
        session,
        user,
        account,
        fecha=date(2026, 8, 7),
        actividad_id=activity.id,
        concepto_id=concept.id,
        tipo_id=kind.id,
        estado=EstadoTransaccion.TIPIFICADO,
    )
    make_transaction(
        session,
        user,
        account,
        fecha=date(2026, 8, 7),
        actividad_id=activity.id,
        concepto_id=other_concept.id,
        tipo_id=other_kind.id,
        estado=EstadoTransaccion.TIPIFICADO,
    )
    make_transaction(
        session,
        user,
        account,
        fecha=date(2026, 8, 8),
        actividad_id=activity.id,
        concepto_id=concept.id,
        tipo_id=kind.id,
        estado=EstadoTransaccion.TIPIFICADO,
    )

    response = client.get(
        "/api/v1/transacciones",
        params={
            "fecha_desde": "2026-08-07",
            "fecha_hasta": "2026-08-07",
            "actividad_id": str(activity.id),
            "concepto_id": str(concept.id),
            "tipo_id": str(kind.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(expected.id)


def test_operational_patch_rejects_financial_fields_and_audits_allowed_changes(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    transaction = make_transaction(
        session, user, account, n_operacion="OP-FIJA", monto=Decimal("10")
    )
    branch = Sucursal(nombre="Norte", codigo="NORTE")
    session.add(branch)
    session.commit()

    assert (
        client.patch(f"/api/v1/transacciones/{transaction.id}", json={"monto": "20"}).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/transacciones/{transaction.id}", json={"n_operacion": "OP-OTRA"}
        ).status_code
        == 422
    )
    response = client.patch(
        f"/api/v1/transacciones/{transaction.id}",
        json={
            "sucursal_id": str(branch.id),
            "documento": "DOC-EDITADO",
            "observaciones": "Revisado",
        },
    )

    assert response.status_code == 200
    assert response.json()["n_operacion"] == "OP-FIJA"
    assert response.json()["monto"] == "10.00"
    assert response.json()["documento"] == "DOC-EDITADO"
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == transaction.id, AuditLog.accion == AuditAction.UPDATE
        )
    )
    assert audit is not None
    assert set(audit.cambios) == {"sucursal_id", "documento", "observaciones"}


def test_anular_requires_admin_and_hides_transaction_by_default(client_and_session):
    client, session, user = client_and_session
    account = make_account(session)
    transaction = make_transaction(session, user, account)

    assert client.patch(f"/api/v1/transacciones/{transaction.id}/anular").status_code == 403
    admin = User(
        email="admin@example.com",
        hashed_password="unused",
        nombre="Admin",
        rol=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    session.add(admin)
    session.commit()
    app.dependency_overrides[get_current_user] = lambda: admin
    response = client.patch(f"/api/v1/transacciones/{transaction.id}/anular")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/api/v1/transacciones").json()["total"] == 0
    assert client.get(f"/api/v1/transacciones/{transaction.id}").status_code == 200
    assert client.patch(f"/api/v1/transacciones/{transaction.id}/anular").status_code == 409
    audit = session.scalar(
        select(AuditLog).where(
            AuditLog.registro_id == transaction.id, AuditLog.accion == AuditAction.SOFT_DELETE
        )
    )
    assert audit is not None
    assert audit.cambios["accion"] == "anulado"
