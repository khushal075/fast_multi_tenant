"""
Shared pytest fixtures for fast_multi_tenant tests.

Strategy:
- Unit tests use an in-memory SQLite DB via aiosqlite (no Postgres needed)
- Integration tests use the real Postgres instance via config.local.env
- The test app overrides get_db so routes use the test session
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.tenant import Tenant
from app.models.role import Role
from app.database.session import get_db
from app.core.tenant_context import set_current_tenant, _tenant_id_ctx
from app.main import app


# ── In-memory async SQLite engine ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest_asyncio.fixture
async def db_session(engine):
    """
    Creates all tables fresh for each test, yields an AsyncSession,
    then drops everything. Tests are fully isolated.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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
async def client(db_session: AsyncSession, tenant: Tenant):
    """
    Async test client with:
    - get_db overridden to use the in-memory test session
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
async def anon_client():
    """Test client with no tenant header — for public routes."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c