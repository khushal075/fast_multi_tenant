import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database.base import PublicBase


class Tenant(PublicBase):
    """
    Central tenant registry. Lives in the public schema.
    Inherits from PublicBase — does NOT get a tenant_id column
    (it IS the tenant, it doesn't belong to one).
    """
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)