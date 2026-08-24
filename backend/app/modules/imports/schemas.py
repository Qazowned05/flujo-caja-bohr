import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportErrorDetail(BaseModel):
    fila: int
    mensaje: str


class ImportDuplicateDetail(BaseModel):
    fila: int
    n_operacion: str
    motivo: str


class ImportResponse(BaseModel):
    batch_id: uuid.UUID | None
    total_filas: int
    filas_nuevas: int
    filas_duplicadas: int
    filas_error: int
    duplicados: list[ImportDuplicateDetail]
    errores: list[ImportErrorDetail]


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_bancaria_id: uuid.UUID
    archivo_nombre: str
    usuario_id: uuid.UUID
    fecha_importacion: datetime
    total_filas: int
    filas_nuevas: int
    filas_duplicadas: int
    filas_error: int
