from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.database.session import SessionLocal
from app.core.tenant_context import set_current_tenant
from app.models.tenant import Tenant

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")

        if tenant_id:
            db = SessionLocal()
            try:
                tenant = db.query(Tenant).filter(
                    Tenant.tenant_id == tenant_id,
                    Tenant.is_active == True,
                ).first()

                if not tenant:
                    raise HTTPException(status_code=403, detail="Invalid or inactive tenant.")
                set_current_tenant(tenant.schema_name)
            finally:
                db.close()
        return await call_next(request)