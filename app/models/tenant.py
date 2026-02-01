from time import timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = ({'schema': 'public'})
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    schema_name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, unique=True)