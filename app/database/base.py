from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """
    All models should inherit from this class.
    They will automatically get useful metadata and naming conventions
    """

    # Automatically generate table name from class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Every table in the platform needs audit timestamp
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
