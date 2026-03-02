import asyncio
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database.session import SyncSessionLocal
from app.core.tenant_context import set_current_tenant, _tenant_id_ctx
from app.models.tenant import Tenant


class TenantMiddleware(BaseHTTPMiddleware):
    # Exact paths that bypass tenant resolution
    PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    # Path prefixes that bypass tenant resolution
    # Tenant provisioning must be public — you need to create a tenant
    # before you have a tenant ID to authenticate with
    PUBLIC_PREFIXES = ("/api/v1/tenants",)

    def _is_public(self, path: str) -> bool:
        if path in self.PUBLIC_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES)

    async def dispatch(self, request: Request, call_next):
        if self._is_public(request.url.path):
            return await call_next(request)

        tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "X-Tenant-ID header is required."},
            )

        # Run sync DB lookup in threadpool — keeps the event loop unblocked
        loop = asyncio.get_event_loop()
        tenant = await loop.run_in_executor(None, self._resolve_tenant, tenant_id)

        if not tenant:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid or inactive tenant."},
            )

        # Store tenant UUID in context for the duration of this request
        token = _tenant_id_ctx.set(tenant.id)
        set_current_tenant(tenant.id)

        try:
            response = await call_next(request)
            return response
        finally:
            _tenant_id_ctx.reset(token)

    def _resolve_tenant(self, tenant_id: str):
        """
        Sync DB lookup — runs in a threadpool via run_in_executor.
        Uses SyncSessionLocal (sync engine) — async sessions cannot
        be used inside run_in_executor.
        """
        db = SyncSessionLocal()
        try:
            return (
                db.query(Tenant)
                .filter(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True,
                )
                .first()
            )
        finally:
            db.close()