"""
Integration tests — exercises full FastAPI request/response cycle.
Uses real Postgres via the db_session fixture (transaction rolled back after each test).
Covers: public routes, tenant CRUD, missing header handling, inactive tenant.
"""
import uuid
import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


# ── Public Routes ─────────────────────────────────────────────────────────────

class TestPublicRoutes:

    @pytest.mark.asyncio
    async def test_root_returns_200(self, anon_client: AsyncClient):
        response = await anon_client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, anon_client: AsyncClient):
        response = await anon_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_docs_accessible(self, anon_client: AsyncClient):
        response = await anon_client.get("/docs")
        assert response.status_code == 200


# ── Tenant Middleware ─────────────────────────────────────────────────────────

class TestTenantMiddleware:

    @pytest.mark.asyncio
    async def test_missing_tenant_header_returns_400(self, anon_client: AsyncClient):
        response = await anon_client.get("/debug/context")
        assert response.status_code == 400
        assert "X-Tenant-ID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_returns_403(self, anon_client: AsyncClient):
        """
        Middleware queries real DB — mock _resolve_tenant to return None
        simulating a tenant not found, without needing real DB tables.
        """
        with patch(
            "app.middleware.tenant_gate.TenantMiddleware._resolve_tenant",
            return_value=None
        ):
            response = await anon_client.get(
                "/debug/context",
                headers={"X-Tenant-ID": str(uuid.uuid4())},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_tenant_passes_through(self, anon_client: AsyncClient, tenant_context):
        """
        Mock _resolve_tenant to return the test tenant directly —
        bypasses SyncSessionLocal which can't see the test transaction.
        tenant_context sets the ContextVar so /debug/context returns it.
        """
        with patch(
            "app.middleware.tenant_gate.TenantMiddleware._resolve_tenant",
            return_value=tenant_context,
        ):
            response = await anon_client.get(
                "/debug/context",
                headers={"X-Tenant-ID": str(tenant_context.id)},
            )
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data


# ── Tenant Provisioning ───────────────────────────────────────────────────────

class TestTenantProvisioning:

    @pytest.mark.asyncio
    async def test_create_tenant(self, anon_client: AsyncClient, db_session: AsyncSession):
        from app.database.session import get_db
        from app.main import app

        async def override():
            yield db_session

        app.dependency_overrides[get_db] = override

        response = await anon_client.post(
            "/api/v1/tenants/",
            json={"name": "New Corp"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Corp"
        assert data["is_active"] is True
        assert "id" in data

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_duplicate_tenant_returns_409(
        self, anon_client: AsyncClient, db_session: AsyncSession
    ):
        from app.database.session import get_db
        from app.main import app

        async def override():
            yield db_session

        app.dependency_overrides[get_db] = override

        await anon_client.post("/api/v1/tenants/", json={"name": "Dupe Corp"})
        response = await anon_client.post("/api/v1/tenants/", json={"name": "Dupe Corp"})
        assert response.status_code == 409

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_tenant_name_too_short(self, anon_client: AsyncClient):
        response = await anon_client.post(
            "/api/v1/tenants/",
            json={"name": "X"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_tenants(self, client: AsyncClient):
        response = await client.get("/api/v1/tenants/")
        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_tenant_by_id(self, client: AsyncClient, tenant: Tenant):
        response = await client.get(f"/api/v1/tenants/{tenant.id}")
        assert response.status_code == 200
        assert response.json()["id"] == str(tenant.id)

    @pytest.mark.asyncio
    async def test_get_nonexistent_tenant_returns_404(self, client: AsyncClient):
        response = await client.get(f"/api/v1/tenants/{uuid.uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_tenant(self, client: AsyncClient, tenant: Tenant):
        response = await client.patch(f"/api/v1/tenants/{tenant.id}/deactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_returns_409(
        self, client: AsyncClient, tenant: Tenant
    ):
        await client.patch(f"/api/v1/tenants/{tenant.id}/deactivate")
        response = await client.patch(f"/api/v1/tenants/{tenant.id}/deactivate")
        assert response.status_code == 409