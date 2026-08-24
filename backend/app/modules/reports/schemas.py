import uuid
from typing import Any

from pydantic import BaseModel


class ReporteError(BaseModel):
    fila: int
    mensaje: str


class ReporteCambio(BaseModel):
    fila: int
    transaccion_id: uuid.UUID
    cambios: dict[str, Any]


class ActualizacionMasivaResponse(BaseModel):
    confirmar: bool
    aplicado: bool
    total_filas: int
    filas_validas: int
    filas_error: int
    errores: list[ReporteError]
    cambios: list[ReporteCambio]
