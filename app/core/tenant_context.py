import uuid
from contextvars import ContextVar
from typing import Optional

# Stores the tenant's UUID for the duration of the current request.
# ContextVar is safe for concurrent async requests — each request gets
# its own isolated value, they cannot leak into each other.
_tenant_id_ctx: ContextVar[Optional[uuid.UUID]] = ContextVar("tenant_id", default=None)


def set_current_tenant(tenant_id: uuid.UUID) -> None:
    """Set the tenant UUID for the current request context."""
    _tenant_id_ctx.set(tenant_id)


def get_current_tenant() -> Optional[uuid.UUID]:
    """
    Retrieve the tenant UUID for the current request.
    Returns None if called outside a tenant request context.
    """
    return _tenant_id_ctx.get()