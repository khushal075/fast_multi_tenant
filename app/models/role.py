from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base, TenantMixin


class Role(TenantMixin, Base):
    """
    Tenant-scoped role. Gets tenant_id automatically from TenantMixin.
    Roles are isolated per tenant — 'admin' in tenant A is separate from tenant B.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    users = relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role(name='{self.name}', tenant='{self.tenant_id}')>"