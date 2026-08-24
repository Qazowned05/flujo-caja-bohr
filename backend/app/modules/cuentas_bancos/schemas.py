import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_initial_balance(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("saldo_inicial debe ser finito.")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BancoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    codigo: str = Field(min_length=1, max_length=50)


class BancoUpdate(BancoCreate):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    codigo: str | None = Field(default=None, min_length=1, max_length=50)


class BancoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    codigo: str
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CuentaBancariaCreate(BaseModel):
    banco_id: uuid.UUID
    alias: str = Field(min_length=1, max_length=255)
    numero_cuenta: str = Field(min_length=1, max_length=100)
    moneda: str = Field(pattern=r"^[A-Za-z]{3}$")
    saldo_inicial: Decimal = Field(default=Decimal("0.00"))

    @field_validator("moneda")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("saldo_inicial")
    @classmethod
    def validate_initial_balance(cls, value: Decimal) -> Decimal:
        return normalize_initial_balance(value)


class CuentaBancariaUpdate(BaseModel):
    banco_id: uuid.UUID | None = None
    alias: str | None = Field(default=None, min_length=1, max_length=255)
    numero_cuenta: str | None = Field(default=None, min_length=1, max_length=100)
    moneda: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    saldo_inicial: Decimal | None = None

    @field_validator("moneda")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("saldo_inicial")
    @classmethod
    def validate_initial_balance(cls, value: Decimal | None) -> Decimal | None:
        return normalize_initial_balance(value) if value is not None else value


class CuentaBancariaRead(CuentaBancariaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
