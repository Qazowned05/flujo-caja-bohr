import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.transacciones.models import EstadoTransaccion, OrigenTransaccion


class TransaccionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documento: str | None = Field(default=None, max_length=255)
    observaciones: str | None = None
    sucursal_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    concepto_id: uuid.UUID | None = None
    tipo_id: uuid.UUID | None = None
    proyeccion_id: uuid.UUID | None = None


class TransaccionMaterializar(BaseModel):
    """Campos ajustables al confirmar una proyeccion."""

    model_config = ConfigDict(extra="forbid")

    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1)
    n_operacion: str = Field(min_length=1, max_length=255)
    monto: Decimal | None = None
    documento: str | None = Field(default=None, max_length=255)
    observaciones: str | None = None
    sucursal_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    concepto_id: uuid.UUID | None = None
    tipo_id: uuid.UUID | None = None

    @field_validator("descripcion", "n_operacion", mode="before")
    @classmethod
    def strip_required_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            raise ValueError("Este campo no puede estar vacio.")
        return value

    @field_validator("fecha", "descripcion", "monto")
    @classmethod
    def validate_required_fields(
        cls, value: date | str | Decimal | None
    ) -> date | str | Decimal | None:
        if value is None:
            raise ValueError("Este campo no puede ser nulo.")
        if isinstance(value, Decimal) and (not value.is_finite() or value == 0):
            raise ValueError("monto debe ser finito y distinto de cero.")
        return value


class TransaccionProyeccionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    descripcion: str = Field(min_length=1)
    monto: Decimal
    cuenta_bancaria_id: uuid.UUID
    documento: str | None = Field(default=None, max_length=255)
    observaciones: str | None = None
    sucursal_id: uuid.UUID | None = None
    vendedor_id: uuid.UUID | None = None
    actividad_id: uuid.UUID | None = None
    concepto_id: uuid.UUID | None = None
    tipo_id: uuid.UUID | None = None

    @field_validator("descripcion", mode="before")
    @classmethod
    def validate_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("descripcion no puede estar vacia.")
        return value

    @field_validator("monto")
    @classmethod
    def validate_monto(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value == 0:
            raise ValueError("monto debe ser finito y distinto de cero.")
        return value


class TransaccionManualCreate(TransaccionProyeccionCreate):
    n_operacion: str = Field(min_length=1, max_length=255)

    @field_validator("n_operacion", mode="before")
    @classmethod
    def strip_n_operacion(cls, value: str) -> str:
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            raise ValueError("n_operacion no puede estar vacio.")
        return value


class UsuarioTransaccionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str


class TransaccionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha: date
    descripcion: str
    n_operacion: str | None
    monto: Decimal
    moneda: str
    documento: str | None
    observaciones: str | None
    sucursal_id: uuid.UUID | None
    vendedor_id: uuid.UUID | None
    actividad_id: uuid.UUID | None
    concepto_id: uuid.UUID | None
    tipo_id: uuid.UUID | None
    cuenta_bancaria_id: uuid.UUID
    origen: OrigenTransaccion
    estado: EstadoTransaccion
    materializado: bool
    import_batch_id: uuid.UUID | None
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID
    updated_by_id: uuid.UUID
    created_by: UsuarioTransaccionRead
    updated_by: UsuarioTransaccionRead


class TransaccionListRead(BaseModel):
    items: list[TransaccionRead]
    total: int
    offset: int
    limit: int
