from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text

from alembic import context

# Import the base modal so that alembic can see the desired state
from app.core.config import settings
from app.models import Base

config = context.config


# Interpret the config file for python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Build connection logic using our principal settings
    configuration = config.get_section(config.config_ini_section, {})
    configuration['sqlalchemy.url'] = settings.SQLALCHEMY_DATABASE_URI

    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Migrate the Shared / Public Schema first
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema='public'
        )

        with context.begin_transaction():
            context.run_migrations()

        # Migrate Tenant Schemas
        # Fetch all the tenant schema from master table

        result = connection.execute(text("select count(*) from public.tenants"))
        schemas =[row[0] for row in result]
        for schema in schemas:
            print(f'Migrating schema {schema}')
            connection.execute(text(f"SET search_path TO {schema}"))

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                schema=schema, # Forces migrations to run against this specific schema
            )

            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    # For simplicity, we usually run multitenant migration online
    pass
else:
    run_migrations_online()
