import io
import uuid
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.modules.ganancias_perdidas.routes import TEMPLATE_HEADERS
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
    previous = settings.profit_and_loss_enabled
    settings.profit_and_loss_enabled = True
    with TestClient(app) as client:
        yield client, user
    settings.profit_and_loss_enabled = previous
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def test_imported_entries_build_a_traceable_profit_loss_summary(client_and_session):
    client, _ = client_and_session
    center = client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "200", "nombre": "Administracion"}
    )
    assert center.status_code == 201
    income_parent = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={"codigo": "INGRESOS", "nombre": "Ingresos", "naturaleza": "INGRESO"},
    ).json()
    expense_parent = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={"codigo": "GASTOS", "nombre": "Gastos", "naturaleza": "GASTO_OPERATIVO"},
    ).json()
    income = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={
            "codigo": "VENTAS",
            "nombre": "Ventas",
            "naturaleza": "INGRESO",
            "padre_id": income_parent["id"],
        },
    )
    expense = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={
            "codigo": "PERSONAL",
            "nombre": "Personal",
            "naturaleza": "GASTO_OPERATIVO",
            "padre_id": expense_parent["id"],
        },
    )
    assert income.status_code == expense.status_code == 201

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Asientos"
    sheet.append(TEMPLATE_HEADERS)
    sheet.append(
        ["2026-06", "Ingresos", "Ventas", 1000, "200", "", "Factura", ""]
    )
    sheet.append(
        ["2026-06", "Gastos", "Personal", 300, "200", "", "Planilla", ""]
    )
    output = io.BytesIO()
    workbook.save(output)
    response = client.post(
        "/api/v1/ganancias-perdidas/importar.xlsx",
        files={
            "archivo": (
                "junio.xlsx",
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201
    assert response.json()["filas_nuevas"] == 2

    invalid_workbook = Workbook()
    invalid_sheet = invalid_workbook.active
    invalid_sheet.title = "Asientos"
    invalid_sheet.append(TEMPLATE_HEADERS)
    invalid_sheet.append(["2026-06", "Ingresos", "Personal", 100, "200", "", "Invalido", ""])
    invalid_output = io.BytesIO()
    invalid_workbook.save(invalid_output)
    invalid = client.post(
        "/api/v1/ganancias-perdidas/importar.xlsx",
        files={
            "archivo": (
                "invalido.xlsx",
                invalid_output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert invalid.status_code == 422
    assert "no corresponde al rubro" in invalid.json()["detail"]["errores"][0]["mensaje"]

    summary = client.get(
        "/api/v1/ganancias-perdidas/resumen?fecha_desde=2026-06-01&fecha_hasta=2026-06-30"
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["ingresos_netos"] == "1000.00"
    assert body["gastos_operativos"] == "-300.00"
    assert body["utilidad_neta"] == "700.00"
    entries = client.get("/api/v1/ganancias-perdidas/asientos").json()
    assert len(entries) == 2
    imported = entries[0]
    edited = client.patch(
        f"/api/v1/ganancias-perdidas/asientos/{imported['id']}",
        json={
            "fecha": imported["fecha"],
            "descripcion": "Factura corregida",
            "documento": imported["documento"],
            "moneda": imported["moneda"],
            "debe": imported["debe"],
            "haber": imported["haber"],
            "centro_resultado_id": imported["centro_resultado_id"],
            "rubro_id": imported["rubro_id"],
            "observaciones": imported["observaciones"],
        },
    )
    assert edited.status_code == 200
    assert edited.json()["descripcion"] == "Factura corregida"
    report = client.get(
        "/api/v1/ganancias-perdidas/reporte.xlsx?fecha_desde=2026-06-01&fecha_hasta=2026-06-30"
    )
    assert report.status_code == 200
    workbook = load_workbook(io.BytesIO(report.content))
    assert [cell.value for cell in workbook["Asientos EGyP"][1]][:5] == [
        "Fecha", "Periodo", "Codigo rubro", "Rubro", "Naturaleza"
    ]


def test_advisor_cannot_change_profit_loss_catalogues(client_and_session):
    client, user = client_and_session
    user.rol = UserRole.ASESOR
    response = client.post(
        "/api/v1/ganancias-perdidas/centros",
        json={"codigo": "200", "nombre": "Administracion"},
    )
    assert response.status_code == 403


def test_distribution_rule_can_apply_to_any_category(client_and_session):
    client, _ = client_and_session
    first = client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "300", "nombre": "Santa Natura"}
    ).json()
    second = client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "310", "nombre": "FQP"}
    ).json()
    rubro = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={"codigo": "PERSONAL", "nombre": "Personal", "naturaleza": "GASTO_OPERATIVO"},
    ).json()
    rule = client.post(
        "/api/v1/ganancias-perdidas/reglas-distribucion",
        json={
            "nombre": "Planilla compartida",
            "lineas": [
                {"centro_resultado_id": first["id"], "porcentaje": "60"},
                {"centro_resultado_id": second["id"], "porcentaje": "40"},
            ],
        },
    )
    assert rule.status_code == 201
    updated_rule = client.patch(
        f"/api/v1/ganancias-perdidas/reglas-distribucion/{rule.json()['id']}",
        json={
            "nombre": "Planilla compartida",
            "lineas": [
                {"centro_resultado_id": first["id"], "porcentaje": "60"},
                {"centro_resultado_id": second["id"], "porcentaje": "40"},
            ],
        },
    )
    assert updated_rule.status_code == 200
    shared = client.post(
        "/api/v1/ganancias-perdidas/asientos",
        json={
            "fecha": "2026-06-30",
            "cuenta_contable": "621101",
            "descripcion": "Planilla compartida",
            "rubro_id": rubro["id"],
            "regla_distribucion_id": rule.json()["id"],
            "debe": "100",
            "haber": "0",
        },
    )
    assert shared.status_code == 201
    assert shared.json()["es_resultado"] is False
    explicit = client.post(
        "/api/v1/ganancias-perdidas/asientos",
        json={
            "fecha": "2026-06-30",
            "cuenta_contable": "621101",
            "descripcion": "Planilla asignada",
            "rubro_id": rubro["id"],
            "centro_resultado_id": first["id"],
            "debe": "50",
            "haber": "0",
        },
    )
    assert explicit.status_code == 201
    summary = client.get("/api/v1/ganancias-perdidas/resumen").json()
    row = next(item for item in summary["rubros"] if item["codigo"] == "PERSONAL")
    assert row["por_centro"] == {"300": "-110.00", "310": "-40.00"}


def test_distribution_rules_can_overlap_and_extend_their_validity(client_and_session):
    client, _ = client_and_session
    first = client.post(
        "/api/v1/ganancias-perdidas/centros",
        json={"codigo": "300", "nombre": "Santa Natura"},
    ).json()
    second = client.post(
        "/api/v1/ganancias-perdidas/centros",
        json={"codigo": "310", "nombre": "FQP"},
    ).json()
    first_rule = {
        "nombre": "Alquiler junio",
        "vigente_desde": "2026-06-01",
        "vigente_hasta": "2026-06-30",
        "lineas": [
            {"centro_resultado_id": first["id"], "porcentaje": "60"},
            {"centro_resultado_id": second["id"], "porcentaje": "40"},
        ],
    }
    created = client.post("/api/v1/ganancias-perdidas/reglas-distribucion", json=first_rule)
    assert created.status_code == 201
    overlapping = client.post(
        "/api/v1/ganancias-perdidas/reglas-distribucion",
        json={
            **first_rule,
            "nombre": "Alquiler junio revisado",
            "vigente_desde": "2026-06-30",
        },
    )
    assert overlapping.status_code == 201
    extended = client.patch(
        f"/api/v1/ganancias-perdidas/reglas-distribucion/{created.json()['id']}",
        json={**first_rule, "vigente_hasta": "2026-07-31"},
    )
    assert extended.status_code == 200
    next_rule = client.post(
        "/api/v1/ganancias-perdidas/reglas-distribucion",
        json={
            **first_rule,
            "nombre": "Alquiler julio",
            "vigente_desde": "2026-08-01",
            "vigente_hasta": None,
        },
    )
    assert next_rule.status_code == 201
    conflicting_extension = client.patch(
        f"/api/v1/ganancias-perdidas/reglas-distribucion/{created.json()['id']}",
        json={**first_rule, "vigente_hasta": "2026-08-31"},
    )
    assert conflicting_extension.status_code == 200


def test_template_requires_a_rubro_and_guides_the_user(client_and_session):
    client, _ = client_and_session
    client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "300", "nombre": "Santa Natura"}
    )
    parent = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={"codigo": "INGRESOS", "nombre": "Ingresos", "naturaleza": "INGRESO"},
    ).json()
    client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={
            "codigo": "VENTAS",
            "nombre": "Ventas",
            "naturaleza": "INGRESO",
            "padre_id": parent["id"],
        },
    )
    template = client.get("/api/v1/ganancias-perdidas/plantilla.xlsx")
    workbook = load_workbook(io.BytesIO(template.content))
    assert {"Asientos", "Lineas de negocio", "Rubros", "Guia de tipificacion", "Listas rubros"} <= set(workbook.sheetnames)
    assert [cell.value for cell in workbook["Asientos"][1]] == TEMPLATE_HEADERS
    validations = {str(validation.sqref): validation.formula1 for validation in workbook["Asientos"].data_validations.dataValidation}
    assert set(validations) == {
        "B2:B5000", "C2:C5000", "E2:E5000", "F2:F5000"
    }
    assert validations["C2:C5000"].startswith("=INDIRECT(IFERROR(VLOOKUP($B2")
    assert workbook["Listas rubros"].sheet_state == "hidden"

    invalid = client.post(
        "/api/v1/ganancias-perdidas/asientos",
        json={
            "fecha": "2026-06-30",
            "cuenta_contable": "701101",
            "descripcion": "Venta sin linea",
            "rubro_id": client.get("/api/v1/ganancias-perdidas/rubros").json()[0]["id"],
            "haber": "100",
        },
    )
    assert invalid.status_code == 422


def test_history_filters_roots_and_hard_deletes_a_complete_distribution(client_and_session):
    client, _ = client_and_session
    first = client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "300", "nombre": "Santa Natura"}
    ).json()
    second = client.post(
        "/api/v1/ganancias-perdidas/centros", json={"codigo": "310", "nombre": "FQP"}
    ).json()
    rubro = client.post(
        "/api/v1/ganancias-perdidas/rubros",
        json={"codigo": "PERSONAL", "nombre": "Personal", "naturaleza": "GASTO_OPERATIVO"},
    ).json()
    rule = client.post(
        "/api/v1/ganancias-perdidas/reglas-distribucion",
        json={
            "nombre": "Personal compartido",
            "lineas": [
                {"centro_resultado_id": first["id"], "porcentaje": "60"},
                {"centro_resultado_id": second["id"], "porcentaje": "40"},
            ],
        },
    )
    created = client.post(
        "/api/v1/ganancias-perdidas/asientos",
        json={
            "fecha": "2026-06-30",
            "descripcion": "Planilla junio",
            "observaciones": "Revision pendiente",
            "rubro_id": rubro["id"],
            "regla_distribucion_id": rule.json()["id"],
            "debe": "100",
        },
    )
    assert created.status_code == 201
    history = client.get(
        "/api/v1/ganancias-perdidas/asientos?solo_origen=true&busqueda=revision"
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    entries = client.get("/api/v1/ganancias-perdidas/asientos").json()
    distributed = next(entry for entry in entries if entry["asiento_origen_id"])
    assert distributed["regla_distribucion_nombre"] == "Personal compartido"
    assert distributed["porcentaje_distribucion"] in {"60.00", "60"}
    deleted = client.request(
        "DELETE",
        "/api/v1/ganancias-perdidas/asientos",
        json={"ids": [distributed["id"]]},
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/ganancias-perdidas/asientos").json() == []
