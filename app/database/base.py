import uuid
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func


class PublicBase(DeclarativeBase):
    """
    Base for shared / infrastructure tables that live in the public schema
    and are NOT scoped to a tenant. Example: Tenant registry itself.
    These tables do NOT get a tenant_id column.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class TenantBase(DeclarativeBase):
    """
    Base for all tenant-scoped tables.
    Every model that inherits from this automatically gets:
      - tenant_id   (UUID, FK → public.tenants.id, non-nullable, indexed)
      - created_at
      - updated_at

    This enforces row-level isolation at the platform level — no model
    can accidentally be created without tenant scoping.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)