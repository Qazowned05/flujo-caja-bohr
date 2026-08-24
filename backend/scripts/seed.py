"""Carga datos de demostracion idempotentes usando un administrador existente."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.categorias.models import Actividad, Concepto, Tipo
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria
from app.modules.divisas.models import TipoCambio
from app.modules.imports.models import ImportBatch
from app.modules.sucursales.models import Sucursal
from app.modules.transacciones.models import EstadoTransaccion, OrigenTransaccion, Transaccion
from app.modules.usuarios.models import User, UserRole
from app.modules.vendedores.models import Vendedor


def get_or_create(db, model, defaults: dict, **filters):
    record = db.scalar(select(model).filter_by(**filters))
    if record:
        if hasattr(record, "is_active"):
            record.is_active = True
            record.deleted_at = None
        return record
    record = model(**(defaults | filters))
    db.add(record)
    db.flush()
    return record


def main() -> None:
    with SessionLocal() as db:
        admin = db.scalar(
            select(User)
            .where(User.rol == UserRole.ADMIN, User.is_active.is_(True))
            .order_by(User.created_at)
        )
        if not admin:
            raise SystemExit(
                "Se requiere un usuario administrador activo antes de ejecutar el seed."
            )

        bcp = get_or_create(db, Banco, {"nombre": "BCP"}, codigo="BCP")
        interbank = get_or_create(db, Banco, {"nombre": "Interbank"}, codigo="INTERBANK")
        bcp_pen = get_or_create(
            db,
            CuentaBancaria,
            {
                "banco_id": bcp.id,
                "alias": "BCP Soles",
                "moneda": "PEN",
                "saldo_inicial": Decimal("25000.00"),
            },
            banco_id=bcp.id,
            numero_cuenta="SEED-BCP-PEN-001",
        )
        bcp_usd = get_or_create(
            db,
            CuentaBancaria,
            {
                "banco_id": bcp.id,
                "alias": "BCP Dolares",
                "moneda": "USD",
                "saldo_inicial": Decimal("5000.00"),
            },
            banco_id=bcp.id,
            numero_cuenta="SEED-BCP-USD-001",
        )
        interbank_pen = get_or_create(
            db,
            CuentaBancaria,
            {
                "banco_id": interbank.id,
                "alias": "Interbank Soles",
                "moneda": "PEN",
                "saldo_inicial": Decimal("12000.00"),
            },
            banco_id=interbank.id,
            numero_cuenta="SEED-IBK-PEN-001",
        )
        central = get_or_create(db, Sucursal, {"nombre": "Central"}, codigo="SEED-CENTRAL")
        miraflores = get_or_create(db, Sucursal, {"nombre": "Miraflores"}, codigo="SEED-MIRAFLORES")
        ana = get_or_create(
            db, Vendedor, {"nombre": "Ana Torres", "sucursal_id": central.id}, codigo="SEED-ANA"
        )
        luis = get_or_create(
            db, Vendedor, {"nombre": "Luis Rojas", "sucursal_id": miraflores.id}, codigo="SEED-LUIS"
        )
        ventas = get_or_create(db, Actividad, {"nombre": "Ventas"}, nombre="Ventas")
        gastos = get_or_create(
            db, Actividad, {"nombre": "Gastos operativos"}, nombre="Gastos operativos"
        )
        cobros = get_or_create(
            db, Concepto, {"nombre": "Cobros"}, actividad_id=ventas.id, nombre="Cobros"
        )
        proveedores = get_or_create(
            db,
            Concepto,
            {"nombre": "Proveedores"},
            actividad_id=gastos.id,
            nombre="Proveedores",
        )
        contado = get_or_create(
            db, Tipo, {"nombre": "Contado"}, concepto_id=cobros.id, nombre="Contado"
        )
        transferencia = get_or_create(
            db, Tipo, {"nombre": "Transferencia"}, concepto_id=cobros.id, nombre="Transferencia"
        )
        pago = get_or_create(
            db, Tipo, {"nombre": "Pago"}, concepto_id=proveedores.id, nombre="Pago"
        )
        get_or_create(
            db,
            TipoCambio,
            {
                "tasa": Decimal("3.750000"),
                "created_by_id": admin.id,
                "updated_by_id": admin.id,
            },
            moneda_origen="USD",
            moneda_destino="PEN",
            fecha_vigencia=date.today(),
        )
        batch = get_or_create(
            db,
            ImportBatch,
            {
                "cuenta_bancaria_id": bcp_pen.id,
                "usuario_id": admin.id,
                "total_filas": 2,
                "filas_nuevas": 2,
                "filas_duplicadas": 0,
                "filas_error": 0,
            },
            archivo_nombre="seed_movimientos.csv",
        )

        today = date.today()
        transactions = [
            (
                "SEED-IMP-001",
                today - timedelta(days=7),
                "Deposito pendiente semilla",
                Decimal("1250.00"),
                bcp_pen,
                OrigenTransaccion.IMPORTADO,
                EstadoTransaccion.PENDIENTE_TIPIFICAR,
                False,
                None,
                None,
                None,
                batch.id,
            ),
            (
                "SEED-IMP-002",
                today - timedelta(days=6),
                "Cargo bancario pendiente semilla",
                Decimal("-85.50"),
                bcp_pen,
                OrigenTransaccion.IMPORTADO,
                EstadoTransaccion.PENDIENTE_TIPIFICAR,
                False,
                None,
                None,
                None,
                batch.id,
            ),
            (
                "SEED-MAN-001",
                today - timedelta(days=5),
                "Venta manual Central",
                Decimal("2300.00"),
                bcp_pen,
                OrigenTransaccion.MANUAL,
                EstadoTransaccion.TIPIFICADO,
                False,
                ventas.id,
                cobros.id,
                contado.id,
                None,
            ),
            (
                "SEED-MAN-002",
                today - timedelta(days=4),
                "Pago manual proveedor",
                Decimal("-640.00"),
                interbank_pen,
                OrigenTransaccion.MANUAL,
                EstadoTransaccion.TIPIFICADO,
                False,
                gastos.id,
                proveedores.id,
                pago.id,
                None,
            ),
            (
                None,
                today + timedelta(days=2),
                "Cobro proyectado Lima",
                Decimal("1800.00"),
                bcp_pen,
                OrigenTransaccion.PROYECCION,
                EstadoTransaccion.PROYECTADO,
                False,
                ventas.id,
                cobros.id,
                transferencia.id,
                None,
            ),
            (
                None,
                today + timedelta(days=5),
                "Pago proyectado servicios",
                Decimal("-420.00"),
                interbank_pen,
                OrigenTransaccion.PROYECCION,
                EstadoTransaccion.PROYECTADO,
                False,
                gastos.id,
                proveedores.id,
                pago.id,
                None,
            ),
            (
                "SEED-PROJ-MAT-001",
                today - timedelta(days=2),
                "Proyeccion materializada USD",
                Decimal("550.00"),
                bcp_usd,
                OrigenTransaccion.PROYECCION,
                EstadoTransaccion.CONFIRMADO,
                True,
                ventas.id,
                cobros.id,
                transferencia.id,
                None,
            ),
            (
                "SEED-MAN-003",
                today - timedelta(days=1),
                "Venta manual Miraflores",
                Decimal("975.00"),
                bcp_pen,
                OrigenTransaccion.MANUAL,
                EstadoTransaccion.TIPIFICADO,
                False,
                ventas.id,
                cobros.id,
                contado.id,
                None,
            ),
        ]
        for (
            operation,
            tx_date,
            description,
            amount,
            account,
            origin,
            state,
            materialized,
            activity_id,
            concept_id,
            type_id,
            batch_id,
        ) in transactions:
            existing = db.scalar(select(Transaccion).where(Transaccion.descripcion == description))
            if existing:
                continue
            db.add(
                Transaccion(
                    fecha=tx_date,
                    descripcion=description,
                    n_operacion=operation,
                    monto=amount,
                    moneda=account.moneda,
                    cuenta_bancaria_id=account.id,
                    origen=origin,
                    estado=state,
                    materializado=materialized,
                    sucursal_id=central.id if "Central" in description else miraflores.id,
                    vendedor_id=ana.id if "Central" in description else luis.id,
                    actividad_id=activity_id,
                    concepto_id=concept_id,
                    tipo_id=type_id,
                    import_batch_id=batch_id,
                    created_by_id=admin.id,
                    updated_by_id=admin.id,
                )
            )
        db.commit()
    print("Datos de prueba cargados correctamente.")


if __name__ == "__main__":
    main()
