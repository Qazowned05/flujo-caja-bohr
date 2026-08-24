import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash
from app.modules.shared.audit import log_audit
from app.modules.shared.models import AuditAction
from app.modules.usuarios.deps import get_current_user, require_admin
from app.modules.usuarios.models import User
from app.modules.usuarios.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("", response_model=list[UserRead])
def list_users(
    _: Annotated[User, Depends(require_admin)], db: Annotated[Session, Depends(get_db)]
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    email = user_in.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El email ya esta registrado."
        )

    user = User(
        email=email,
        nombre=user_in.nombre,
        hashed_password=get_password_hash(user_in.password),
        rol=user_in.rol,
        is_superuser=user_in.rol.value == "admin",
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        user=current_user,
        table=User.__tablename__,
        record_id=user.id,
        action=AuditAction.CREATE,
        changes={"email": email, "nombre": user.nombre, "rol": user.rol.value},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    values = user_in.model_dump(exclude_unset=True)
    changes = {
        field: {"old": getattr(user, field), "new": value}
        for field, value in values.items()
        if field != "password" and getattr(user, field) != value
    }
    if "password" in values:
        user.hashed_password = get_password_hash(values.pop("password"))
        changes["password"] = {"updated": True}
    for field, value in values.items():
        setattr(user, field, value)
    if user_in.rol is not None:
        user.is_superuser = user_in.rol.value == "admin"
    action = AuditAction.UPDATE
    if user_in.is_active is False:
        user.deleted_at = datetime.now(UTC)
        action = AuditAction.SOFT_DELETE
        changes["deleted_at"] = {"new": user.deleted_at}
    elif user_in.is_active is True:
        user.deleted_at = None
    if changes:
        log_audit(
            db,
            user=current_user,
            table=User.__tablename__,
            record_id=user.id,
            action=action,
            changes=changes,
        )
    db.commit()
    db.refresh(user)
    return user
