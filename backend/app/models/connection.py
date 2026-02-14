"""
Connection Profile Model - Stores User Operational Database configurations
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum


class ConnectionType(str, enum.Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MARIADB = "mariadb"


class ConnectionGroup(str, enum.Enum):
    """Connection environment groups."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    ANALYTICS = "analytics"
    TESTING = "testing"


class ConnectionMode(str, enum.Enum):
    """Connection access modes."""
    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    MAINTENANCE = "maintenance"


class HealthStatus(str, enum.Enum):
    """Connection health status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ConnectionProfile(Base):
    """User Operational Database connection profile."""
    __tablename__ = "connection_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Database type and environment
    db_type = Column(String(50), nullable=False, default=ConnectionType.POSTGRESQL.value)
    connection_group = Column(String(50), nullable=False, default=ConnectionGroup.DEVELOPMENT.value)
    connection_mode = Column(String(50), nullable=False, default=ConnectionMode.READ_WRITE.value)
    
    # Connection details
    host = Column(String(255), nullable=True)  # Nullable for mongodb
    port = Column(Integer, nullable=True)
    database = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=True)  # Encrypted at rest
    schema = Column(String(255), nullable=True, default="public")
    
    # SSL/TLS Configuration
    ssl_enabled = Column(Boolean, default=False, nullable=False)
    ssl_cert_path = Column(String(500), nullable=True)
    ssl_key_path = Column(String(500), nullable=True)
    ssl_ca_path = Column(String(500), nullable=True)
    
    # Connection Pool Settings
    pool_size = Column(Integer, default=5, nullable=False)
    max_connections = Column(Integer, default=10, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)
    
    # Health Monitoring
    health_status = Column(String(50), default=HealthStatus.UNKNOWN.value, nullable=False)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)
    
    # Database Capabilities (auto-detected)
    capabilities = Column(JSON, nullable=True)  # {version, features, extensions}
    db_metadata = Column(JSON, nullable=True)  # Additional DB-specific metadata (renamed from metadata)
    
    # Settings
    is_active = Column(Boolean, default=False, nullable=False)
    is_read_only = Column(Boolean, default=False, nullable=False)  # DEPRECATED: Use connection_mode
    is_default = Column(Boolean, default=False, nullable=False)  # Default connection for new operations
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # User ID
    
    # Credential Security
    credential_last_rotated = Column(DateTime(timezone=True), nullable=True)
    credential_expires_at = Column(DateTime(timezone=True), nullable=True)
    credential_rotation_days = Column(Integer, default=90, nullable=False)  # Auto-rotation interval
    encryption_key_version = Column(Integer, default=1, nullable=False)  # Track which key was used
    encrypted_connection_string = Column(Text, nullable=True)  # Store full connection URI if provided
    
    def get_connection_string(self, decrypted_password: str = None, decrypted_connection_string: str = None) -> str:
        """Generate connection string from profile."""
        if decrypted_connection_string:
            return decrypted_connection_string
            
        password = decrypted_password or ""
        
        if self.db_type == ConnectionType.POSTGRESQL:
            return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == ConnectionType.MONGODB:
            if self.username and password:
                return f"mongodb://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
            else:
                return f"mongodb://{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_display_name(self) -> str:
        """Get user-friendly display name with environment badge."""
        return f"{self.name} ({self.connection_group.value.title()})"
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.health_status == HealthStatus.ONLINE
