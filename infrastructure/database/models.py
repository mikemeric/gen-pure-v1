"""
SQLAlchemy models for the detection system

Defines database schema for:
- Users (authentication)
- Sessions (user sessions)
- DetectionResults (detection history)
- ApiKeys (API access)
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    User model for authentication
    
    Stores user credentials, roles, and metadata.
    Passwords are hashed with bcrypt before storage.
    """
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Credentials
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100))
    company = Column(String(100))
    
    # Roles and permissions
    roles = Column(JSON, nullable=False, default=list)  # ['user', 'admin', etc.]
    permissions = Column(JSON, nullable=False, default=list)  # ['detect', 'calibrate', etc.]
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    detection_results = relationship("DetectionResult", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
        Index('idx_user_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'company': self.company,
            'roles': self.roles,
            'permissions': self.permissions,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Session(Base):
    """
    User session model
    
    Tracks active user sessions with refresh tokens.
    Used for token invalidation and session management.
    """
    __tablename__ = 'sessions'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Session data
    refresh_token_hash = Column(String(255), unique=True, nullable=False, index=True)
    access_token_jti = Column(String(255), index=True)  # JWT ID for revocation
    
    # Client info
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_id', 'user_id'),
        Index('idx_session_token', 'refresh_token_hash'),
        Index('idx_session_active', 'is_active', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class DetectionResult(Base):
    """
    Detection result model
    
    Stores history of all detection operations with metadata.
    """
    __tablename__ = 'detection_results'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Detection data
    image_path = Column(String(500))
    image_hash = Column(String(64), index=True)  # SHA-256 of image
    
    # Results
    niveau_y = Column(Integer)  # Pixel position
    niveau_percentage = Column(Float)  # Percentage (0-100)
    niveau_ml = Column(Float)  # Volume in mL (if calibrated)
    
    confiance = Column(Float, nullable=False)  # Confidence score (0-1)
    methode_utilisee = Column(String(50))  # 'hough', 'clustering', etc.
    
    # Performance
    temps_traitement_ms = Column(Float)  # Processing time
    
    # Metadata
    image_width = Column(Integer)
    image_height = Column(Integer)
    calibration_used = Column(Boolean, default=False)
    erreurs = Column(JSON, default=list)  # List of errors if any
    metadata = Column(JSON, default=dict)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="detection_results")
    
    # Indexes
    __table_args__ = (
        Index('idx_detection_user_id', 'user_id'),
        Index('idx_detection_created', 'created_at'),
        Index('idx_detection_hash', 'image_hash'),
    )
    
    def __repr__(self):
        return f"<DetectionResult(id={self.id}, niveau={self.niveau_percentage}%, confiance={self.confiance})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_path': self.image_path,
            'niveau_y': self.niveau_y,
            'niveau_percentage': self.niveau_percentage,
            'niveau_ml': self.niveau_ml,
            'confiance': self.confiance,
            'methode_utilisee': self.methode_utilisee,
            'temps_traitement_ms': self.temps_traitement_ms,
            'image_width': self.image_width,
            'image_height': self.image_height,
            'calibration_used': self.calibration_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ApiKey(Base):
    """
    API key model for programmatic access
    
    Allows users to create API keys for non-interactive authentication.
    """
    __tablename__ = 'api_keys'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Key data
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    name = Column(String(100), nullable=False)  # User-friendly name
    
    # Permissions
    permissions = Column(JSON, default=list)  # Subset of user permissions
    
    # Rate limiting
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime)  # Optional expiration
    last_used = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_apikey_user_id', 'user_id'),
        Index('idx_apikey_hash', 'key_hash'),
        Index('idx_apikey_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"


# Database initialization function
def create_tables(engine):
    """
    Create all tables in the database
    
    Args:
        engine: SQLAlchemy engine
    
    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine('postgresql://...')
        >>> create_tables(engine)
    """
    Base.metadata.create_all(engine)
    print("✅ Database tables created")


def drop_tables(engine):
    """
    Drop all tables from the database
    
    Args:
        engine: SQLAlchemy engine
    
    Warning:
        This will delete all data!
    """
    Base.metadata.drop_all(engine)
    print("⚠️  Database tables dropped")
