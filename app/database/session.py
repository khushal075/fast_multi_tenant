from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# ── Async engine — used by all FastAPI route handlers ─────────────────────────
async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    echo=False,  # set True locally for SQL debugging, never in production
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency — yields an async DB session and guarantees cleanup.

    Usage:
        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            tenant_id = get_current_tenant()
            result = await db.execute(
                select(User).where(User.tenant_id == tenant_id)
            )
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Sync engine — used only by middleware (run_in_executor) and seed scripts ──
# Keeping a separate sync engine avoids mixing sync/async SQLAlchemy sessions,
# which are not interchangeable and cause subtle runtime errors.
sync_engine = create_engine(
    # swap driver back to plain psycopg (no +asyncpg) for sync connections
    settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+psycopg", "postgresql+psycopg"),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    echo=False,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)