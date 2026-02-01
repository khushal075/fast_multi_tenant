import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import engine
from app.database.base import Base

# Ensure User is imported so Base.metadata knows about it
from app.models.user import User
from app.core.tenant_context import set_current_tenant

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_seed():
    logger.info("--- Starting Multi-tenant Seed ---")

    # Step 1: Create Schema and Infrastructure
    # We use a separate connection with 'commit' to ensure the schema exists
    with engine.connect() as conn:
        with conn.begin():
            logger.info("Creating 'tenants' table in public...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    schema_name VARCHAR(255) UNIQUE NOT NULL
                );
            """))

            logger.info("Creating schema 'tenant_default'...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS tenant_default;"))

            logger.info("Inserting default tenant record...")
            conn.execute(text("""
                INSERT INTO tenants (name, schema_name) 
                VALUES ('Default Tenant', 'tenant_default')
                ON CONFLICT (name) DO NOTHING;
            """))

    # Step 2: Create ORM Tables (Users, etc.)
    # Note: We use engine.connect() + manual transaction to ensure SET search_path sticks
    with engine.connect() as conn:
        with conn.begin():
            try:
                logger.info("Syncing ORM models into 'tenant_default'...")

                # 1. Set the context for any subsequent session-based logic
                set_current_tenant('default')

                # 2. FORCE the search path on this specific connection
                # This ensures Postgres puts 'users' in 'tenant_default'
                conn.execute(text("SET search_path TO tenant_default, public"))

                # 3. Create the tables
                Base.metadata.create_all(bind=conn)

                logger.info(f"DEBUG: Models found in Base: {list(Base.metadata.tables.keys())}")
                logger.info("--- Seed Complete: 'tenant_default' is ready with tables! ---")

            except Exception as e:
                logger.error(f"Table Sync Failed: {e}")
                raise e


if __name__ == "__main__":
    run_seed()