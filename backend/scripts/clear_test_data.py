"""Remove test data while retaining application users and Alembic metadata."""

from sqlalchemy import text

from app.core.database import engine

PRESERVED_TABLES = {"usuarios", "alembic_version"}


def quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace("\"", "\"\"")}"'


def main() -> None:
    with engine.begin() as connection:
        table_names = connection.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        ).scalars().all()
        tables_to_clear = [name for name in table_names if name not in PRESERVED_TABLES]

        if not tables_to_clear:
            print("No tables to clear.")
            return

        tables = ", ".join(f"public.{quote_identifier(name)}" for name in tables_to_clear)
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY"))
        cleared_counts = {
            name: connection.execute(
                text(f"SELECT count(*) FROM public.{quote_identifier(name)}")
            ).scalar_one()
            for name in tables_to_clear
        }
        user_count = connection.execute(text("SELECT count(*) FROM public.usuarios")).scalar_one()

        print(f"Cleared: {', '.join(tables_to_clear)}")
        print(f"Records remaining in cleared tables: {sum(cleared_counts.values())}")
        print(f"Users retained: {user_count}")
        print("Preserved: usuarios, alembic_version")


if __name__ == "__main__":
    main()
