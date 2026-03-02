import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse, TenantListResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new tenant",
)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Provisions a new tenant in the system.

    - Creates a row in public.tenants
    - Returns the tenant UUID — clients must pass this as X-Tenant-ID on all
      subsequent requests

    This endpoint does NOT require an X-Tenant-ID header (it's in PUBLIC_PATHS).
    In production, protect this with an admin API key or internal network policy.
    """
    # Check for name collision before inserting
    existing = await db.execute(
        select(Tenant).where(Tenant.name == payload.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tenant named '{payload.name}' already exists.",
        )

    tenant = Tenant(
        id=uuid.uuid4(),
        name=payload.name,
        is_active=True,
    )
    db.add(tenant)
    await db.flush()   # gets the DB-generated created_at without committing yet
    await db.refresh(tenant)

    return tenant


@router.get(
    "/",
    response_model=TenantListResponse,
    summary="List all tenants",
)
async def list_tenants(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all tenants. In production, restrict to internal/admin use only.
    """
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()

    return TenantListResponse(tenants=tenants, total=len(tenants))


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get a tenant by ID",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    return tenant


@router.patch(
    "/{tenant_id}/deactivate",
    response_model=TenantResponse,
    summary="Deactivate a tenant",
)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Marks a tenant as inactive. Their data is preserved but they can no
    longer authenticate via X-Tenant-ID (TenantMiddleware will reject them).
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found.",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant is already inactive.",
        )

    tenant.is_active = False
    await db.flush()
    await db.refresh(tenant)

    return tenant