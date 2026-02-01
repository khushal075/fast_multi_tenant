# Import all models so that alembic can find them via Base.metadata

from app.database.base import Base
from app.models.tenant import Tenant