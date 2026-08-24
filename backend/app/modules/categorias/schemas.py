import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActividadCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    orden: int = Field(default=0, ge=0)


class ActividadUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    orden: int | None = Field(default=None, ge=0)


class ActividadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    orden: int
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConceptoCreate(BaseModel):
    actividad_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=255)
    incluye_flujo_bruto_operativo: bool = False
    incluye_flujo_neto_operativo: bool = False


class ConceptoUpdate(BaseModel):
    actividad_id: uuid.UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    incluye_flujo_bruto_operativo: bool | None = None
    incluye_flujo_neto_operativo: bool | None = None


class ConceptoRead(ConceptoCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TipoCreate(BaseModel):
    concepto_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=255)


class TipoUpdate(BaseModel):
    concepto_id: uuid.UUID | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=255)


class TipoRead(TipoCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
