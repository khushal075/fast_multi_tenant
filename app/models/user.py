from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import TenantBase


class User(TenantBase):
    """
    Tenant-scoped user. Inherits tenant_id from TenantBase automatically.
    Every query against this table must filter by tenant_id for row-level isolation.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

    role = relationship("Role", back_populates="users")

    def __repr__(self):
        return f"<User(email='{self.email}', tenant='{self.tenant_id}')>"