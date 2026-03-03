import uuid
import logging
from sqlalchemy.orm import Session

from app.database.session import sync_engine, SyncSessionLocal
from app.database.base import Base
from app.models.tenant import Tenant
from app.models.role import Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_seed():
    logger.info("--- Starting seed ---")

    Base.metadata.create_all(bind=sync_engine)
    logger.info("Tables created.")

    db: Session = SyncSessionLocal()
    try:
        existing = db.query(Tenant).filter_by(name="Default Tenant").first()
        if not existing:
            tenant = Tenant(id=uuid.uuid4(), name="Default Tenant", is_active=True)
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            logger.info(f"Created tenant: {tenant.name} (id={tenant.id})")

            for role_name in ("admin", "member", "viewer"):
                db.add(Role(
                    tenant_id=tenant.id,
                    name=role_name,
                    description=f"{role_name.capitalize()} role",
                ))
            db.commit()
            logger.info("Seeded roles: admin, member, viewer")
        else:
            logger.info("Default tenant already exists — skipping.")

    except Exception as e:
        db.rollback()
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        db.close()

    logger.info("--- Seed complete ---")


if __name__ == "__main__":
    run_seed()