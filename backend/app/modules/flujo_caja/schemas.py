import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ResumenGrupoRead(BaseModel):
    moneda: str
    ingresos_reales: Decimal
    egresos_reales: Decimal
    neto_real: Decimal
    ingresos_proyectados: Decimal
    egresos_proyectados: Decimal
    neto_proyectado: Decimal
    neto_total: Decimal
    cantidad_reales: int
    cantidad_proyectadas: int


class ResumenCuentaRead(ResumenGrupoRead):
    cuenta_bancaria_id: uuid.UUID
    cuenta_alias: str
    banco_id: uuid.UUID
    banco_nombre: str


class SaldoFinalRead(BaseModel):
    moneda: str
    saldo_real: Decimal
    saldo_final: Decimal


class FlujoCajaResumenRead(BaseModel):
    fecha_desde: date | None
    fecha_hasta: date | None
    incluir_proyecciones: bool
    por_divisa: list[ResumenGrupoRead]
    por_cuenta: list[ResumenCuentaRead]
    saldos_finales: list[SaldoFinalRead]


class DesgloseTipoRead(BaseModel):
    id: uuid.UUID | None
    nombre: str
    total: Decimal
    valores_por_fecha: dict[str, Decimal]


class DesgloseConceptoRead(DesgloseTipoRead):
    incluye_flujo_bruto_operativo: bool
    incluye_flujo_neto_operativo: bool
    tipos: list[DesgloseTipoRead]


class DesgloseActividadRead(DesgloseTipoRead):
    orden: int
    conceptos: list[DesgloseConceptoRead]


class SaldoPorFechaRead(BaseModel):
    saldo_inicial: Decimal
    saldo_final: Decimal


class FlujoCajaDesgloseTipificacionesRead(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    fechas: list[date]
    moneda_visualizacion: str
    actividades: list[DesgloseActividadRead]
    saldos_por_fecha: dict[str, SaldoPorFechaRead]
    movimientos_diarios_por_fecha: dict[str, Decimal]
    cantidad_movimientos: int
    cantidad_sin_tasa: int
