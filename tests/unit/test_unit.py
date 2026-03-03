"""
Unit tests — no external dependencies, in-memory SQLite DB.
Covers: tenant context, TenantMiddleware logic, models, schemas.
"""
import uuid
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.tenant_context import (
    set_current_tenant,
    get_current_tenant,
    _tenant_id_ctx,
)
from app.models.tenant import Tenant
from app.models.role import Role
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantResponse


# ── Tenant Context ────────────────────────────────────────────────────────────

class TestTenantContext:

    def test_set_and_get_tenant(self):
        tid = uuid.uuid4()
        set_current_tenant(tid)
        assert get_current_tenant() == tid

    def test_default_is_none(self):
        token = _tenant_id_ctx.set(None)
        assert get_current_tenant() is None
        _tenant_id_ctx.reset(token)

    def test_context_resets_correctly(self):
        tid = uuid.uuid4()
        token = _tenant_id_ctx.set(tid)
        assert get_current_tenant() == tid
        _tenant_id_ctx.reset(token)
        # After reset, value returns to whatever it was before
        assert get_current_tenant() != tid or get_current_tenant() is None

    def test_different_uuids_are_isolated(self):
        tid1 = uuid.uuid4()
        tid2 = uuid.uuid4()
        assert tid1 != tid2
        set_current_tenant(tid1)
        assert get_current_tenant() == tid1
        set_current_tenant(tid2)
        assert get_current_tenant() == tid2


# ── Tenant Model ──────────────────────────────────────────────────────────────

class TestTenantModel:

    @pytest.mark.asyncio
    async def test_create_tenant(self, db_session: AsyncSession):
        tenant = Tenant(id=uuid.uuid4(), name="Acme Corp", is_active=True)
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)

        assert tenant.id is not None
        assert tenant.name == "Acme Corp"
        assert tenant.is_active is True
        assert tenant.created_at is not None

    @pytest.mark.asyncio
    async def test_tenant_id_is_uuid(self, db_session: AsyncSession):
        tenant = Tenant(id=uuid.uuid4(), name="UUID Corp", is_active=True)
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        assert isinstance(tenant.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_multiple_tenants_can_be_active(self, db_session: AsyncSession):
        """Verifies the unique=True bug on is_active is fixed."""
        t1 = Tenant(id=uuid.uuid4(), name="Tenant One", is_active=True)
        t2 = Tenant(id=uuid.uuid4(), name="Tenant Two", is_active=True)
        db_session.add_all([t1, t2])
        await db_session.commit()

        result = await db_session.execute(
            select(Tenant).where(Tenant.is_active == True)
        )
        active = result.scalars().all()
        assert len(active) == 2

    @pytest.mark.asyncio
    async def test_deactivate_tenant(self, db_session: AsyncSession):
        tenant = Tenant(id=uuid.uuid4(), name="Old Client", is_active=True)
        db_session.add(tenant)
        await db_session.commit()

        tenant.is_active = False
        await db_session.commit()
        await db_session.refresh(tenant)

        assert tenant.is_active is False


# ── Role Model ────────────────────────────────────────────────────────────────

class TestRoleModel:

    @pytest.mark.asyncio
    async def test_role_has_tenant_id(self, db_session: AsyncSession, tenant: Tenant):
        role = Role(tenant_id=tenant.id, name="admin", description="Admin role")
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)

        assert role.tenant_id == tenant.id
        assert role.name == "admin"

    @pytest.mark.asyncio
    async def test_same_role_name_across_tenants(self, db_session: AsyncSession):
        """Row-level isolation: two tenants can both have an 'admin' role."""
        t1 = Tenant(id=uuid.uuid4(), name="Tenant A", is_active=True)
        t2 = Tenant(id=uuid.uuid4(), name="Tenant B", is_active=True)
        db_session.add_all([t1, t2])
        await db_session.commit()

        r1 = Role(tenant_id=t1.id, name="admin", description="Admin for A")
        r2 = Role(tenant_id=t2.id, name="admin", description="Admin for B")
        db_session.add_all([r1, r2])
        await db_session.commit()

        result = await db_session.execute(select(Role).where(Role.name == "admin"))
        roles = result.scalars().all()
        assert len(roles) == 2
        assert {r.tenant_id for r in roles} == {t1.id, t2.id}

    @pytest.mark.asyncio
    async def test_roles_filtered_by_tenant(self, db_session: AsyncSession):
        """Querying by tenant_id only returns that tenant's roles."""
        t1 = Tenant(id=uuid.uuid4(), name="Filtered A", is_active=True)
        t2 = Tenant(id=uuid.uuid4(), name="Filtered B", is_active=True)
        db_session.add_all([t1, t2])
        await db_session.commit()

        db_session.add(Role(tenant_id=t1.id, name="admin"))
        db_session.add(Role(tenant_id=t1.id, name="viewer"))
        db_session.add(Role(tenant_id=t2.id, name="admin"))
        await db_session.commit()

        result = await db_session.execute(
            select(Role).where(Role.tenant_id == t1.id)
        )
        t1_roles = result.scalars().all()
        assert len(t1_roles) == 2
        assert all(r.tenant_id == t1.id for r in t1_roles)


# ── Schemas ───────────────────────────────────────────────────────────────────

class TestTenantSchemas:

    def test_tenant_create_valid(self):
        payload = TenantCreate(name="Valid Corp")
        assert payload.name == "Valid Corp"

    def test_tenant_create_too_short(self):
        with pytest.raises(Exception):
            TenantCreate(name="X")

    def test_tenant_response_from_orm(self):
        from datetime import datetime, timezone
        tenant = Tenant(
            id=uuid.uuid4(),
            name="ORM Tenant",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        response = TenantResponse.model_validate(tenant)
        assert response.name == "ORM Tenant"
        assert response.is_active is True


# ── TenantMiddleware ──────────────────────────────────────────────────────────

class TestTenantMiddlewareLogic:

    def test_is_public_exact_match(self):
        from app.middleware.tenant_gate import TenantMiddleware
        mw = TenantMiddleware(app=MagicMock())
        assert mw._is_public("/") is True
        assert mw._is_public("/health") is True
        assert mw._is_public("/docs") is True

    def test_is_public_prefix_match(self):
        from app.middleware.tenant_gate import TenantMiddleware
        mw = TenantMiddleware(app=MagicMock())
        assert mw._is_public("/api/v1/tenants") is True
        assert mw._is_public("/api/v1/tenants/some-uuid") is True

    def test_is_not_public(self):
        from app.middleware.tenant_gate import TenantMiddleware
        mw = TenantMiddleware(app=MagicMock())
        assert mw._is_public("/api/v1/users") is False
        assert mw._is_public("/api/v1/roles") is False
        assert mw._is_public("/debug/context") is False