import argparse

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.modules.usuarios.models import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea el administrador inicial.")
    parser.add_argument("email")
    parser.add_argument("nombre")
    parser.add_argument("password")
    args = parser.parse_args()

    email = TypeAdapter(EmailStr).validate_python(args.email).lower()

    with SessionLocal() as session:
        existing_user = session.scalar(select(User).where(User.email == email))
        if existing_user:
            raise SystemExit("Ya existe un usuario con ese email.")

        session.add(
            User(
                email=email,
                nombre=args.nombre,
                hashed_password=get_password_hash(args.password),
                rol=UserRole.ADMIN,
                is_superuser=True,
            )
        )
        session.commit()

    print(f"Administrador creado: {email}")


if __name__ == "__main__":
    main()
