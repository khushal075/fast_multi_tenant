from contextvars import ContextVar
from typing import Optional

# This variable is unique to each 'task' or 'request'
# Even if 1,000 requests hit at once, they won't leak into each other
_tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

def set_current_tenant(tenant_id: str) -> None:
    """Stores the tenant ID for the duration of the current request."""
    _tenant_id_ctx.set(tenant_id)

def get_current_tenant() -> str:
    """Retrieves the tenant ID for the current execution context."""
    return _tenant_id_ctx.get()