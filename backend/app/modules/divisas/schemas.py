import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TipoCambioFields(BaseModel):
    moneda_origen: str = Field(min_length=3, max_length=3)
    moneda_destino: str = Field(min_length=3, max_length=3)
    tasa: Decimal
    fecha_vigencia: date

    @field_validator("moneda_origen", "moneda_destino")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("La moneda debe ser un codigo ISO de tres letras.")
        return value

    @field_validator("tasa")
    @classmethod
    def validate_rate(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value <= 0:
            raise ValueError("tasa debe ser finita y mayor que cero.")
        return value

    @model_validator(mode="after")
    def validate_pair(self):
        if self.moneda_origen == self.moneda_destino:
            raise ValueError("moneda_origen y moneda_destino deben ser distintas.")
        return self


class TipoCambioCreate(TipoCambioFields):
    model_config = ConfigDict(extra="forbid")


class TipoCambioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moneda_origen: str | None = Field(default=None, min_length=3, max_length=3)
    moneda_destino: str | None = Field(default=None, min_length=3, max_length=3)
    tasa: Decimal | None = None
    fecha_vigencia: date | None = None
    is_active: bool | None = None

    @field_validator("moneda_origen", "moneda_destino")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("La moneda debe ser un codigo ISO de tres letras.")
        return value

    @field_validator("tasa")
    @classmethod
    def validate_rate(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (not value.is_finite() or value <= 0):
            raise ValueError("tasa debe ser finita y mayor que cero.")
        return value


class TipoCambioRead(TipoCambioFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    created_by_id: uuid.UUID
    updated_by_id: uuid.UUID
