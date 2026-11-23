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
    ("GASTOS_ADMIN", "Gastos administrativos", NaturalezaRubro.GASTO_OPERATIVO, None, 10),
    ("ALQUILERES", "Alquileres", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 11),
    ("SERVICIOS_TERCEROS", "Servicios terceros", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 12),
    ("SERVICIOS_PUBLICOS", "Servicios públicos", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 13),
    ("CAJA_CHICA_ADMIN", "Caja chica", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 14),
    ("GASTOS_COMPARTIDOS", "Gastos compartidos", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 15),
    ("SUMINISTROS_OFICINA", "Suministros de oficina", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_ADMIN", 16),
    ("GASTOS_PERSONAL", "Gastos de personal", NaturalezaRubro.GASTO_OPERATIVO, None, 20),
    ("PLANILLA", "Planilla", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_PERSONAL", 21),
    ("RXH", "RXH", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_PERSONAL", 22),
    ("APORTES_EMPLEADOR", "Aportes empleador", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_PERSONAL", 23),
    ("IMPUESTOS", "Impuestos", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_PERSONAL", 24),
    ("VARIOS_PERSONAL", "Varios", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_PERSONAL", 25),
    ("GASTOS_LOGISTICOS", "Gastos logísticos", NaturalezaRubro.GASTO_OPERATIVO, None, 30),
    ("TRANSPORTE", "Transporte", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_LOGISTICOS", 31),
    ("ALMACEN", "Almacén", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_LOGISTICOS", 32),
    ("MATERIAL_DESPACHO", "Material de despacho", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_LOGISTICOS", 33),
    ("CAJA_CHICA_LOG", "Caja chica", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_LOGISTICOS", 34),
    ("PUBLICIDAD_MARKETING", "Publicidad y marketing", NaturalezaRubro.GASTO_OPERATIVO, None, 40),
    ("TV", "TV", NaturalezaRubro.GASTO_OPERATIVO, "PUBLICIDAD_MARKETING", 41),
    ("REDES", "Redes", NaturalezaRubro.GASTO_OPERATIVO, "PUBLICIDAD_MARKETING", 42),
    ("PRODUCCION", "Producción", NaturalezaRubro.GASTO_OPERATIVO, "PUBLICIDAD_MARKETING", 43),
    ("INFLUENCERS", "Influencers", NaturalezaRubro.GASTO_OPERATIVO, "PUBLICIDAD_MARKETING", 44),
    ("MERCHANDISING", "Merchandising", NaturalezaRubro.GASTO_OPERATIVO, "PUBLICIDAD_MARKETING", 45),
    ("GASTOS_FINANCIEROS", "Gastos financieros", NaturalezaRubro.GASTO_FINANCIERO, None, 50),
    ("GASTOS_BANCARIOS", "Gastos bancarios", NaturalezaRubro.GASTO_FINANCIERO, "GASTOS_FINANCIEROS", 51),
    ("PRESTAMOS", "Préstamos", NaturalezaRubro.GASTO_FINANCIERO, "GASTOS_FINANCIEROS", 52),
    ("GASTOS_VARIOS", "Gastos varios", NaturalezaRubro.GASTO_OPERATIVO, None, 60),
    ("OTROS", "Otros", NaturalezaRubro.GASTO_OPERATIVO, "GASTOS_VARIOS", 61),
    ("INGRESOS_OPERATIVOS", "Ingresos operativos", NaturalezaRubro.INGRESO, None, 70),
    ("SERVICIOS_TERCEROS_ING", "Servicio a terceros", NaturalezaRubro.INGRESO, "INGRESOS_OPERATIVOS", 71),
    ("INGRESOS_VENTA", "Ingresos por venta", NaturalezaRubro.INGRESO, "INGRESOS_OPERATIVOS", 72),
    ("NOTA_CREDITO", "Nota de crédito", NaturalezaRubro.INGRESO, "INGRESOS_OPERATIVOS", 73),
    ("INGRESOS_REEMBOLSOS", "Ingresos por reembolsos", NaturalezaRubro.INGRESO, "INGRESOS_OPERATIVOS", 74),
    ("PRESTAMOS_RECIBIDOS", "Prestamos recibidos", NaturalezaRubro.INGRESO, "INGRESOS_OPERATIVOS", 75),
    ("COSTOS_MERCADERIA", "COSTOS DIRECTOS", NaturalezaRubro.COSTO_VENTA, None, 80),
    ("COSTO_MERCADERIA", "Costos de mercadería", NaturalezaRubro.COSTO_VENTA, "COSTOS_MERCADERIA", 81),
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
        cost_parent = by_code["COSTOS_MERCADERIA"]
        cost_category = by_code["COSTO_MERCADERIA"]
        cost_parent.nombre = "COSTOS DIRECTOS"
        cost_category.nombre = "Costos de mercadería"
        cost_category.padre_id = cost_parent.id
        cost_category.orden = 81
        session.commit()
    print("Catalogo EGyP BOHR listo")


if __name__ == "__main__":
    main()
