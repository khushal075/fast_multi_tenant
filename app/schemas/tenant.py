import uuid
from pydantic import BaseModel, Field
from datetime import datetime


class TenantCreate(BaseModel):
    """Payload required to provision a new tenant."""
    name: str = Field(..., min_length=2, max_length=255, examples=["Acme Corp"])


class TenantResponse(BaseModel):
    """Returned after a tenant is created or fetched."""
    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]
    total: int