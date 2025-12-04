"""
Database Models - User Management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserTier(str, enum.Enum):
    """User subscription tier"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    
    # Personal Info
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    curp = Column(String(18), unique=True, index=True, nullable=True)
    
    # Status
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING_VERIFICATION)
    tier = Column(SQLEnum(UserTier), default=UserTier.FREE)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    settings = Column(JSON, default={})
    
    # Relationships
    fiscal_profile = relationship("FiscalProfile", back_populates="user", uselist=False)
    documents = relationship("Document", back_populates="user")
    sat_credentials = relationship("SATCredentials", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    cfdis = relationship("CFDI", back_populates="user")
    prestaciones = relationship("PrestacionAnual", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email}>"
