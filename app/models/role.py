from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import TenantBase


class Role(TenantBase):
    """
    Tenant-scoped role. Inherits tenant_id from TenantBase automatically.
    Roles are isolated per tenant — 'admin' in tenant A is unrelated to 'admin' in tenant B.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(name='{self.name}', tenant='{self.tenant_id}')>"