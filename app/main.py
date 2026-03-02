from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.core.tenant_context import get_current_tenant
from app.database.session import get_db
from app.middleware.tenant_gate import TenantMiddleware
from app.api.v1.endpoints.tenants import router as tenants_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant resolution — must be added after CORSMiddleware
# (Starlette applies middleware in reverse registration order)
app.add_middleware(TenantMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

# Tenant provisioning — no X-Tenant-ID required (listed in PUBLIC_PATHS)
app.include_router(tenants_router, prefix=settings.API_V1_STR)

# Future routers follow this pattern:
# from app.api.v1.endpoints.users import router as users_router
# app.include_router(users_router, prefix=settings.API_V1_STR)

# ── Public routes ─────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def read_root():
    return {"message": f"{settings.PROJECT_NAME} is running"}


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


# ── Debug ─────────────────────────────────────────────────────────────────────

@app.get("/debug/context", tags=["debug"])
async def debug_context(db: AsyncSession = Depends(get_db)):
    """
    Returns current tenant context and DB connection info.
    Requires X-Tenant-ID. Remove before production.
    """
    result = await db.execute(
        text("SELECT current_database(), current_user, current_schemas(false)")
    )
    info = result.fetchone()

    return {
        "tenant_id": str(get_current_tenant()),
        "database": info[0],
        "user": info[1],
        "active_schemas": info[2],
    }