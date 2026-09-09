import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.ganancias_perdidas.models import NaturalezaRubro, OrigenAsientoResultado


class CentroResultadoCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=255)
    orden: int = Field(default=0, ge=0)


class CentroResultadoUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    orden: int | None = Field(default=None, ge=0)


class CentroResultadoRead(CentroResultadoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None


class RubroResultadoCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=255)
    naturaleza: NaturalezaRubro
    padre_id: uuid.UUID | None = None
    orden: int = Field(default=0, ge=0)


class RubroResultadoUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    naturaleza: NaturalezaRubro | None = None
    padre_id: uuid.UUID | None = None
    orden: int | None = Field(default=None, ge=0)


class RubroResultadoRead(RubroResultadoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool
    deleted_at: datetime | None


class ReglaDistribucionLineaCreate(BaseModel):
    centro_resultado_id: uuid.UUID
    porcentaje: Decimal = Field(gt=0, le=100)


class ReglaDistribucionCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    rubro_id: uuid.UUID
    vigente_desde: date | None = None
    vigente_hasta: date | None = None
    lineas: list[ReglaDistribucionLineaCreate] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_rule(self):
        if self.vigente_desde and self.vigente_hasta and self.vigente_desde > self.vigente_hasta:
            raise ValueError("vigente_desde no puede ser posterior a vigente_hasta.")
        if sum(line.porcentaje for line in self.lineas) != Decimal("100"):
            raise ValueError("Los porcentajes deben sumar exactamente 100.")
        if len({line.centro_resultado_id for line in self.lineas}) != len(self.lineas):
            raise ValueError("Un centro no puede repetirse en una regla.")
        return self


class ReglaDistribucionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    rubro_id: uuid.UUID
    vigente_desde: date | None
    vigente_hasta: date | None
    is_active: bool
    lineas: list[ReglaDistribucionLineaCreate]


class AsientoResultadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    fecha: date
    cuenta_contable: str | None
    descripcion: str
    documento: str | None
    moneda: str
    debe: Decimal
    haber: Decimal
    centro_resultado_id: uuid.UUID | None
    rubro_id: uuid.UUID
    observaciones: str | None
    lote_id: uuid.UUID | None
    origen: OrigenAsientoResultado
    asiento_origen_id: uuid.UUID | None
    es_resultado: bool
    motivo_anulacion: str | None
    is_active: bool


class AsientoResultadoCreate(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=1)
    documento: str | None = Field(default=None, max_length=255)
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    debe: Decimal = Field(default=Decimal("0"), ge=0)
    haber: Decimal = Field(default=Decimal("0"), ge=0)
    centro_resultado_id: uuid.UUID | None = None
    rubro_id: uuid.UUID
    observaciones: str | None = None

    @model_validator(mode="after")
    def validate_amount(self):
        if self.debe == 0 and self.haber == 0:
            raise ValueError("debe y haber no pueden ser ambos cero.")
        return self


class AsientoResultadoUpdate(AsientoResultadoCreate):
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1)
    moneda: str | None = Field(default=None, min_length=3, max_length=3)
    debe: Decimal | None = Field(default=None, ge=0)
    haber: Decimal | None = Field(default=None, ge=0)
    rubro_id: uuid.UUID | None = None


class AnularAsientoResultado(BaseModel):
    motivo: str = Field(min_length=3)


class ResultadoRubroRead(BaseModel):
    rubro_id: uuid.UUID
    codigo: str
    nombre: str
    naturaleza: NaturalezaRubro
    padre_id: uuid.UUID | None
    total: Decimal
    por_centro: dict[str, Decimal]


class RentabilidadCentroResultadoRead(BaseModel):
    centro_id: uuid.UUID
    codigo: str
    nombre: str
    ingresos_brutos: Decimal
    ingresos_netos: Decimal
    utilidad_bruta: Decimal
    utilidad_neta: Decimal


class ResumenGananciasPerdidasRead(BaseModel):
    fecha_desde: date | None
    fecha_hasta: date | None
    centros: list[CentroResultadoRead]
    rubros: list[ResultadoRubroRead]
    ingresos_brutos: Decimal
    ingresos_netos: Decimal
    utilidad_bruta: Decimal
    gastos_operativos: Decimal
    utilidad_operativa: Decimal
    utilidad_neta: Decimal
    rentabilidad_por_centro: list[RentabilidadCentroResultadoRead]


class ImportResultadoRead(BaseModel):
    lote_id: uuid.UUID
    total_filas: int
    filas_nuevas: int
