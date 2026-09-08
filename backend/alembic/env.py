from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings
from app.core.database import Base
from app.modules.categorias.models import Actividad, Concepto, Tipo  # noqa: F401
from app.modules.cuentas_bancos.models import Banco, CuentaBancaria  # noqa: F401
from app.modules.divisas.models import TipoCambio  # noqa: F401
from app.modules.ganancias_perdidas.models import (  # noqa: F401
    AsientoResultado,
    CentroResultado,
    LoteResultado,
    MapeoResultado,
    RubroResultado,
)
from app.modules.imports.models import ImportBatch  # noqa: F401
from app.modules.shared.models import AuditLog  # noqa: F401
from app.modules.sucursales.models import Sucursal  # noqa: F401
from app.modules.transacciones.models import Transaccion  # noqa: F401
from app.modules.usuarios.models import User  # noqa: F401
from app.modules.vendedores.models import Vendedor  # noqa: F401

config = context.config
# ConfigParser reserves percent signs for interpolation; encoded database passwords use them.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
