from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.tenant_context import get_current_tenant

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    echo=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tenant isolation engine hook
from sqlalchemy import event


# 1. REMOVE the @event.listens_for(engine, "before_cursor_execute") code entirely.

# 2. ADD THIS instead:
@event.listens_for(engine, "connect")
def set_on_connect(dbapi_connection, connection_record):
    """Sets the search path immediately upon establishing a new connection."""
    # This is great for a base default
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO public")
    cursor.close()


@event.listens_for(SessionLocal, "after_begin")
def set_search_path_on_begin(session, transaction, connection):
    """
    Triggers at the start of every DB session.
    This is the most reliable place for Psycopg 3.
    """
    tenant_id = get_current_tenant()
    schema_name = f"tenant_{tenant_id}" if tenant_id else 'public'

    # We use the connection provided by the session start
    connection.exec_driver_sql(f"SET search_path TO {schema_name}, public")
    print(f"--- PATH SET TO {schema_name} ---")