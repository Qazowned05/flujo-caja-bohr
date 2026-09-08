"""Create initial EGyP account mappings from the BOHR BASE GASTOS categories."""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.ganancias_perdidas.models import MapeoResultado, RubroResultado
from app.modules.ganancias_perdidas.routes import legacy_account, legacy_rows

CATEGORY_TO_RUBRO = {
    "PERSONAL": "PERSONAL",
    "TRANSPORTE": "LOGISTICA",
    "ALQUILER": "ADMIN_SERVICIOS",
    "PUBLICIDAD Y MARKETING": "PUBLICIDAD_MARKETING",
    "LOGISTICA": "LOGISTICA",
    "GASTOS BANCARIOS": "GASTOS_VARIOS",
    "SERV MANTENIMIENTO": "ADMIN_SERVICIOS",
    "SERVICIOS PUBLICOS": "ADMIN_SERVICIOS",
    "SERVICIOS TERCEROS": "ADMIN_SERVICIOS",
    "TRIBUTOS": "GASTOS_VARIOS",
    "SEGUROS": "GASTOS_VARIOS",
    "SUMINISTROS EMBALAJES": "LOGISTICA",
    "COMBUSTIBLE": "LOGISTICA",
    "UTILES OFICINA": "ADMIN_SERVICIOS",
    "GASTOS VARIOS": "GASTOS_VARIOS",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archivo", type=Path)
    args = parser.parse_args()
    rows = legacy_rows(args.archivo.read_bytes(), args.archivo.name)
    with SessionLocal() as session:
        rubros = {item.codigo: item for item in session.scalars(select(RubroResultado)).all()}
        existing = set(session.scalars(select(MapeoResultado.cuenta_contable)))
        created, skipped = 0, set()
        for _, row, _ in rows:
            account = legacy_account(row[1] if len(row) > 1 else None)
            category = str(row[2] if len(row) > 2 else "").strip().upper()
            rubro_code = CATEGORY_TO_RUBRO.get(category)
            if not account or account in existing:
                continue
            if not rubro_code:
                skipped.add(category)
                continue
            session.add(MapeoResultado(cuenta_contable=account, rubro_id=rubros[rubro_code].id))
            existing.add(account)
            created += 1
        session.commit()
    print(f"Mapeos creados: {created}")
    if skipped:
        print(f"Categorias sin mapeo: {', '.join(sorted(skipped))}")


if __name__ == "__main__":
    main()
