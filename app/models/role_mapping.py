from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class RoleMapping(Base):
    __tablename__ = "role_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    environment = Column(String, nullable=False)
    ad_group = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    application = relationship("Application", back_populates="role_mappings")
    
    __table_args__ = (
        UniqueConstraint('application_id', 'environment', 'ad_group', name='uq_app_env_adgroup'),
        Index('ix_role_mappings_application_id', 'application_id'),
        Index('ix_role_mappings_ad_group', 'ad_group'),
        Index('ix_role_mappings_environment', 'environment'),
    )
