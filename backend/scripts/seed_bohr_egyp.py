"""Create the editable BOHR profit and loss catalogue without importing financial entries."""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.ganancias_perdidas.models import CentroResultado, NaturalezaRubro, RubroResultado

CENTERS = [
    ("200", "Administracion", 10),
    ("300", "Santa Natura", 20),
    ("310", "FQP", 30),
    ("340", "Abbott", 40),
    ("350", "Colichon", 50),
]

RUBROS = [
    ("INGRESOS", "Ingresos operacionales", NaturalezaRubro.INGRESO, None, 10),
    ("VENTAS_MERCADERIA", "Ventas mercaderia", NaturalezaRubro.INGRESO, "INGRESOS", 20),
    ("VENTAS_INGRESO", "Ventas ingreso mercaderia", NaturalezaRubro.INGRESO, "INGRESOS", 30),
    ("PRESTACION_SERVICIO", "Prestacion de servicio", NaturalezaRubro.INGRESO, "INGRESOS", 40),
    ("REEMBOLSOS", "Ingresos por reembolsos", NaturalezaRubro.INGRESO, "INGRESOS", 50),
    (
        "DESCUENTOS",
        "Descuentos, rebajas y bonificaciones",
        NaturalezaRubro.CONTRA_INGRESO,
        None,
        60,
    ),
    ("COSTOS", "Costos de ventas", NaturalezaRubro.COSTO_VENTA, None, 70),
    ("COSTO_VENTA", "Costo de ventas operacionales", NaturalezaRubro.COSTO_VENTA, "COSTOS", 80),
    ("COSTO_SERVICIO", "Costo de servicio", NaturalezaRubro.COSTO_VENTA, "COSTOS", 90),
    ("GASTOS", "Gastos operativos", NaturalezaRubro.GASTO_OPERATIVO, None, 100),
    ("PERSONAL", "Personal", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS", 110),
    (
        "ADMIN_SERVICIOS",
        "Administrativos y servicios",
        NaturalezaRubro.GASTO_OPERATIVO,
        "GASTOS",
        120,
    ),
    ("LOGISTICA", "Logistica", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS", 130),
    (
        "PUBLICIDAD_MARKETING",
        "Publicidad y marketing",
        NaturalezaRubro.GASTO_OPERATIVO,
        "GASTOS",
        140,
    ),
    ("GASTOS_VARIOS", "Gastos varios", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS", 150),
    ("DETRACCIONES", "Detracciones", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS", 160),
    ("INGRESOS_FINANCIEROS", "Ingresos financieros", NaturalezaRubro.INGRESO_FINANCIERO, None, 170),
    ("GASTOS_FINANCIEROS", "Gastos financieros", NaturalezaRubro.GASTO_FINANCIERO, None, 180),
    ("IMPUESTO_RENTA", "Impuesto a la renta", NaturalezaRubro.IMPUESTO, None, 190),
]


def main() -> None:
    with SessionLocal() as session:
        for code, name, order in CENTERS:
            if not session.scalar(select(CentroResultado).where(CentroResultado.codigo == code)):
                session.add(CentroResultado(codigo=code, nombre=name, orden=order))
        session.flush()
        by_code = {item.codigo: item for item in session.scalars(select(RubroResultado)).all()}
        for code, name, nature, parent_code, order in RUBROS:
            if code not in by_code:
                record = RubroResultado(
                    codigo=code,
                    nombre=name,
                    naturaleza=nature,
                    padre_id=by_code[parent_code].id if parent_code else None,
                    orden=order,
                )
                session.add(record)
                session.flush()
                by_code[code] = record
        session.commit()
    print("Catalogo EGyP BOHR listo")


if __name__ == "__main__":
    main()
