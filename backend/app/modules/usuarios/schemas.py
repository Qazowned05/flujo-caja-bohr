import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.usuarios.models import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    rol: UserRole = UserRole.ASESOR


class UserUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    rol: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nombre: str
    rol: UserRole
    is_active: bool
    is_superuser: bool
    created_at: datetime
