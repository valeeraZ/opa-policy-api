from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.database import Base


class CustomPolicy(Base):
    __tablename__ = "custom_policies"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    s3_key = Column(String, nullable=False)
    version = Column(String, nullable=False)
    creator_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
