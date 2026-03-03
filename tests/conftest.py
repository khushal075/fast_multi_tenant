"""
Shared pytest fixtures for fast_multi_tenant tests.

Uses a real Postgres instance — same database as development and CI.
CI spins up Postgres via the service container in ci.yml.
Locally, run: docker-compose up db -d

Each test gets a fully isolated async session wrapped in a transaction
that is rolled back after the test — no data persists between tests.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.database.base import Base
from app.models.tenant import Tenant
from app.models.role import Role
from app.database.session import get_db
from app.core.tenant_context import set_current_tenant, _tenant_id_ctx
from app.main import app


# ── Engine + Tables ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """
    Creates a fresh async engine per test, creates all tables, yields a
    session inside a rolled-back transaction, then drops all tables.
    Each test is fully isolated — no shared state between tests.
    """
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as connection:
        await connection.begin()

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            yield session

        await connection.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Tenant fixture ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    """Creates and returns a test tenant."""
    t = Tenant(id=uuid.uuid4(), name="Test Tenant", is_active=True)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest.fixture
def tenant_context(tenant: Tenant):
    """Sets the tenant UUID in ContextVar as TenantMiddleware would."""
    token = _tenant_id_ctx.set(tenant.id)
    set_current_tenant(tenant.id)
    yield tenant
    _tenant_id_ctx.reset(token)


# ── FastAPI test clients ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, tenant: Tenant) -> AsyncClient:
    """
    Async test client with:
    - get_db overridden to use the transactional test session
    - X-Tenant-ID header pre-set to the test tenant
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": str(tenant.id)},
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client() -> AsyncClient:
    """Test client with no tenant header — for public routes and 400/403 tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c