import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria
from app.modules.imports.models import ImportBatch
from app.modules.shared.models import AuditLog
from app.modules.transacciones.models import Transaccion
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
        id=uuid.uuid4(),
        email="asesor@example.com",
        hashed_password="unused",
        nombre="Asesor",
        rol=UserRole.ASESOR,
        is_active=True,
        is_superuser=False,
    )
    bank = Banco(nombre="Banco", codigo="BANCO")
    session.add_all([user, bank])
    session.flush()
    account = CuentaBancaria(banco_id=bank.id, alias="Principal", numero_cuenta="123", moneda="PEN")
    session.add(account)
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, session, user, account
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def upload(client: TestClient, account_id: uuid.UUID, content: str, import_type: str = "REAL"):
    return client.post(
        "/api/v1/imports/csv",
        data={"cuenta_bancaria_id": str(account_id), "tipo_importacion": import_type},
        files={"archivo": ("movimientos.csv", content, "text/csv")},
    )


def test_imports_new_rows_and_reports_duplicates(client_and_session):
    client, session, _, account = client_and_session
    csv = (
        "fecha,descripcion,n_operacion,monto,documento,sucursal,vendedor,observaciones,actividad,concepto,tipo\n"
        "2026-08-01,Venta,OP-1,10.50,DOC-1,,,nota,,,\n"
        "2026-08-02,Cobro,OP-1,20,,,,,,,\n"
    )

    response = upload(client, account.id, csv)

    assert response.status_code == 200
    body = response.json()
    assert body["filas_nuevas"] == 1
    assert body["filas_duplicadas"] == 1
    assert body["duplicados"] == [{"fila": 3, "n_operacion": "OP-1", "motivo": "archivo"}]
    assert session.scalar(select(Transaccion).where(Transaccion.n_operacion == "OP-1"))
    assert len(list(session.scalars(select(AuditLog)))) == 2

    repeated = upload(client, account.id, csv)
    assert repeated.status_code == 200
    assert repeated.json()["filas_nuevas"] == 0
    assert repeated.json()["filas_duplicadas"] == 2


def test_imports_itf_rows_with_repeated_operation_are_not_deduplicated(client_and_session):
    client, session, _, account = client_and_session
    csv = (
        "fecha,descripcion,n_operacion,monto,documento,sucursal,vendedor,observaciones,actividad,concepto,tipo\n"
        "2026-08-01,ITF por transferencia,0000,-1.50,,,,,,,\n"
        "2026-08-02,Impuesto ITF,0000,-2.00,,,,,,,\n"
    )

    response = upload(client, account.id, csv)

    assert response.status_code == 200
    assert response.json()["filas_nuevas"] == 2
    assert response.json()["filas_duplicadas"] == 0
    transactions = list(session.scalars(select(Transaccion).order_by(Transaccion.fecha)))
    assert [transaction.n_operacion for transaction in transactions] == ["0000", "0000"]
    assert all(transaction.is_itf for transaction in transactions)


def test_imports_projections_with_required_tipifications(client_and_session):
    client, session, _, account = client_and_session
    activity = Actividad(nombre="Operaciones")
    session.add(activity)
    session.flush()
    concept = Concepto(actividad_id=activity.id, nombre="Cobros")
    session.add(concept)
    session.flush()
    kind = Tipo(concepto_id=concept.id, nombre="Proyectado")
    session.add(kind)
    session.commit()
    csv = (
        "fecha,descripcion,monto,actividad,concepto,tipo\n"
        "2026-08-01,Cobro esperado,150.00,Operaciones,Cobros,Proyectado\n"
    )

    response = upload(client, account.id, csv, "PROYECCION")

    assert response.status_code == 200
    transaction = session.scalar(select(Transaccion))
    assert transaction is not None
    assert transaction.n_operacion is None
    assert transaction.origen.value == "PROYECCION"
    assert transaction.estado.value == "PROYECTADO"
    assert transaction.actividad_id == activity.id


def test_invalid_file_is_rejected_without_creating_batch(client_and_session):
    client, session, _, account = client_and_session
    csv = (
        "fecha,descripcion,n_operacion,monto,documento,sucursal,vendedor,observaciones,actividad,concepto,tipo\n"
        "2026/99/99,Venta,OP-1,10,,,,,,,\n"
    )

    response = upload(client, account.id, csv)

    assert response.status_code == 422
    assert response.json()["filas_error"] == 1
    assert session.scalar(select(ImportBatch)) is None


def test_adviser_can_read_only_own_batch(client_and_session):
    client, session, user, account = client_and_session
    own_batch = ImportBatch(
        cuenta_bancaria_id=account.id,
        archivo_nombre="own.csv",
        usuario_id=user.id,
        total_filas=0,
        filas_nuevas=0,
        filas_duplicadas=0,
        filas_error=0,
    )
    other_user = User(
        email="other@example.com",
        hashed_password="unused",
        nombre="Otro",
        rol=UserRole.ASESOR,
        is_active=True,
        is_superuser=False,
    )
    session.add_all([own_batch, other_user])
    session.flush()
    other_batch = ImportBatch(
        cuenta_bancaria_id=account.id,
        archivo_nombre="other.csv",
        usuario_id=other_user.id,
        total_filas=0,
        filas_nuevas=0,
        filas_duplicadas=0,
        filas_error=0,
    )
    session.add(other_batch)
    session.commit()

    assert client.get(f"/api/v1/imports/{own_batch.id}").status_code == 200
    assert client.get(f"/api/v1/imports/{other_batch.id}").status_code == 404
