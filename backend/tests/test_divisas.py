import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.modules.divisas.models import TipoCambio
from app.modules.shared.models import AuditAction, AuditLog
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
        email="admin@example.com",
        hashed_password="unused",
        nombre="Admin",
        rol=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
    )
    session.add(user)
    session.commit()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, session
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_admin_manages_tipo_cambio_and_audits(client_and_session):
    client, session = client_and_session
    payload = {
        "moneda_origen": "usd",
        "moneda_destino": "pen",
        "tasa": "3.750000",
        "fecha_vigencia": "2026-08-19",
    }
    created = client.post("/api/v1/divisas/tipos-cambio", json=payload)
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert created.json()["moneda_origen"] == "USD"
    assert client.post("/api/v1/divisas/tipos-cambio", json=payload).status_code == 409
    updated = client.patch(f"/api/v1/divisas/tipos-cambio/{record_id}", json={"tasa": "3.8"})
    assert updated.status_code == 200
    deleted = client.delete(f"/api/v1/divisas/tipos-cambio/{record_id}")
    assert deleted.status_code == 200
    assert client.get("/api/v1/divisas/tipos-cambio").json() == []
    actions = set(
        session.scalars(select(AuditLog.accion).where(AuditLog.registro_id == uuid.UUID(record_id)))
    )
    assert actions == {AuditAction.CREATE, AuditAction.UPDATE, AuditAction.SOFT_DELETE}
    assert session.get(TipoCambio, uuid.UUID(record_id)).is_active is False
