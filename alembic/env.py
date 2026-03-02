from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.database.base import PublicBase, TenantBase

# Import all models so metadata is fully populated before migrations run
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import Role

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Combine metadata from both bases so all tables are visible to Alembic
target_metadata = [PublicBase.metadata, TenantBase.metadata]


def run_migrations_offline() -> None:
    """
    Generate SQL script without a live DB connection.
    Useful for handing off to a DBA or reviewing changes before applying.
    """
    url = settings.SQLALCHEMY_DATABASE_URI
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="public",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations against a live database.

    Row-level isolation model: all tenant data lives in a single shared schema.
    There is only ONE migration pass — no per-tenant schema loop needed.
    Tenant isolation is enforced by tenant_id columns on every data table,
    not by Postgres schema separation.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.SQLALCHEMY_DATABASE_URI

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table="alembic_version",
            version_table_schema="public",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()