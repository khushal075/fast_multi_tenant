import uuid
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Single declarative base for all models — one shared MetaData object.
    This is required for SQLAlchemy to resolve ForeignKey references across
    models (e.g. roles.tenant_id → public.tenants.id).

    All models inherit from Base. Tenant-scoped models additionally
    inherit from TenantMixin to get the tenant_id column.
    """

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class TenantMixin:
    """
    Mixin that adds tenant_id to any model that needs row-level isolation.

    Usage:
        class User(TenantMixin, Base):
            ...

    Every model with this mixin automatically gets:
      - tenant_id (UUID, FK → public.tenants.id, non-nullable, indexed)

    Because this is a mixin (not a second Base), the FK is resolved
    within the same MetaData as the Tenant model — no cross-metadata errors.
    """

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("public.tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )