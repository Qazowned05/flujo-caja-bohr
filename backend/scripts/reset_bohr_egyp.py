"""Reset BOHR EGyP data and load the approved reporting catalogue."""

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.ganancias_perdidas.models import (
    AsientoResultado,
    CentroResultado,
    LoteResultado,
    ReglaDistribucion,
    ReglaDistribucionLinea,
    RubroResultado,
)
from app.modules.shared.models import AuditLog
from scripts.seed_bohr_egyp import CENTERS, RUBROS


EGYP_TABLES = {
    AsientoResultado.__tablename__,
    CentroResultado.__tablename__,
    LoteResultado.__tablename__,
    ReglaDistribucion.__tablename__,
    RubroResultado.__tablename__,
}


def main() -> None:
    with SessionLocal.begin() as session:
        session.execute(delete(ReglaDistribucionLinea))
        session.execute(delete(ReglaDistribucion))
        session.execute(delete(AsientoResultado))
        session.execute(delete(LoteResultado))
        session.execute(delete(AuditLog).where(AuditLog.tabla.in_(EGYP_TABLES)))

        rubros = list(session.scalars(select(RubroResultado)))
        while rubros:
            parent_ids = {rubro.padre_id for rubro in rubros if rubro.padre_id}
            leaves = [rubro for rubro in rubros if rubro.id not in parent_ids]
            for rubro in leaves:
                session.delete(rubro)
            session.flush()
            rubros = [rubro for rubro in rubros if rubro not in leaves]

        session.execute(delete(CentroResultado))
        for code, name, order in CENTERS:
            session.add(CentroResultado(codigo=code, nombre=name, orden=order))
        session.flush()

        centers = {item.codigo: item for item in session.scalars(select(CentroResultado))}
        rubros_by_code: dict[str, RubroResultado] = {}
        for code, name, nature, parent_code, order in RUBROS:
            record = RubroResultado(
                codigo=code,
                nombre=name,
                naturaleza=nature,
                padre_id=rubros_by_code[parent_code].id if parent_code else None,
                orden=order,
            )
            session.add(record)
            session.flush()
            rubros_by_code[code] = record
    print(f"EGyP reiniciado: {len(centers)} centros y {len(rubros_by_code)} rubros cargados")


if __name__ == "__main__":
    main()
