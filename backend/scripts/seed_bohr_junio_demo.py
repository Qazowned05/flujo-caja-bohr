"""Load a clearly marked June 2026 EGyP simulation from BOHR's approved Excel totals."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.ganancias_perdidas.models import (
    AsientoResultado,
    CentroResultado,
    OrigenAsientoResultado,
    RubroResultado,
)
from app.modules.usuarios.models import User, UserRole

DEMO_DOCUMENT = "DEMO-EGYP-062026"
ENTRIES = [
    ("300", "VENTAS_MERCADERIA", "Ventas Santa Natura", 0, "84739.50"),
    ("310", "VENTAS_MERCADERIA", "Ventas e ingresos FQP", 0, "71470.13"),
    ("340", "PRESTACION_SERVICIO", "Servicios Abbott", 0, "7924.76"),
    ("200", "PRESTACION_SERVICIO", "Servicios administración", 0, "4544.91"),
    ("300", "DESCUENTOS", "Descuentos obtenidos Santa Natura", 0, "26422.12"),
    ("300", "COSTO_VENTA", "Costo de ventas Santa Natura", "48131.98", 0),
    ("310", "COSTO_VENTA", "Costo de ventas FQP", "5504.01", 0),
    ("300", "PERSONAL", "Personal Santa Natura", "40498.24", 0),
    ("300", "ADMIN_SERVICIOS", "Administrativos Santa Natura", "10230.34", 0),
    ("300", "LOGISTICA", "Logística Santa Natura", "2649.90", 0),
    ("300", "PUBLICIDAD_MARKETING", "Marketing Santa Natura", "20382.66", 0),
    ("300", "GASTOS_VARIOS", "Varios Santa Natura", "1673.81", 0),
    ("300", "DETRACCIONES", "Detracciones Santa Natura", "5081.64", 0),
    ("310", "PERSONAL", "Personal FQP", "33577.24", 0),
    ("310", "ADMIN_SERVICIOS", "Administrativos FQP", "2728.62", 0),
    ("310", "GASTOS_VARIOS", "Varios FQP", "2163.26", 0),
    ("340", "PERSONAL", "Personal Abbott", "3541.38", 0),
    ("200", "PERSONAL", "Personal Administración", "17926.01", 0),
    ("200", "ADMIN_SERVICIOS", "Administrativos Administración", "8559.83", 0),
    ("200", "LOGISTICA", "Logística Administración", "649.00", 0),
    ("200", "GASTOS_VARIOS", "Varios Administración", "13324.45", 0),
    ("200", "DETRACCIONES", "Detracciones Administración", "296.34", 0),
]


def main() -> None:
    with SessionLocal() as session:
        if session.scalar(
            select(AsientoResultado).where(AsientoResultado.documento == DEMO_DOCUMENT)
        ):
            print("La simulación junio ya existe")
            return
        user = session.scalar(
            select(User).where(User.rol == UserRole.ADMIN).order_by(User.created_at)
        )
        if not user:
            raise SystemExit("Crea primero un administrador BOHR.")
        centers = {item.codigo: item for item in session.scalars(select(CentroResultado)).all()}
        rubros = {item.codigo: item for item in session.scalars(select(RubroResultado)).all()}
        for center_code, rubro_code, description, debit, credit in ENTRIES:
            session.add(
                AsientoResultado(
                    fecha=date(2026, 6, 30),
                    cuenta_contable=f"DEMO-{rubro_code}",
                    descripcion=description,
                    documento=DEMO_DOCUMENT,
                    moneda="PEN",
                    debe=Decimal(str(debit)),
                    haber=Decimal(str(credit)),
                    centro_resultado_id=centers[center_code].id,
                    rubro_id=rubros[rubro_code].id,
                    observaciones=(
                        "Simulación basada en EGYP COSTOS JUNIO MA. "
                        "No es carga contable fuente."
                    ),
                    origen=OrigenAsientoResultado.MANUAL,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                )
            )
        session.commit()
    print("Simulación junio 2026 cargada")


if __name__ == "__main__":
    main()
