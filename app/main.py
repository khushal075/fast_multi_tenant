
from fastapi import FastAPI, Request
from sqlalchemy import text
from starlette.responses import HTMLResponse

from app.core.tenant_context import set_current_tenant, _tenant_id_ctx, get_current_tenant
from app.database.session import SessionLocal

app = FastAPI()

# ---- ADD MIDDLE-WARE ----
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-Id")

    token = _tenant_id_ctx.set(tenant_id)

    # This sets the stage so SQLAlchemy listener fixed earlier knows which schema to use
    set_current_tenant(tenant_id)
    try:
        response = await call_next(request)
        return response
    finally:
        # Reset the context for the next request in this thread / worker
        _tenant_id_ctx.reset(token)

# ----- YOUR ROUTES FOLLOW ----
@app.get("/")
async def read_root():
    return {
        "message": "Multi-tenant API is alive"
    }

@app.get("/test-db")
def test_db():
    db = SessionLocal()
    try:
        # This will tell us the exact database name and current user
        info = db.execute(text("SELECT current_database(), current_user, current_schemas(false)")).fetchone()
        return {
            "database": info[0],
            "user": info[1],
            "active_schemas": info[2],
            "tenant_id": get_current_tenant()
        }
    finally:
        db.close()

