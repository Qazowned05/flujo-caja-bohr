import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SucursalCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    codigo: str = Field(min_length=1, max_length=50)


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    codigo: str | None = Field(default=None, min_length=1, max_length=50)


class SucursalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
