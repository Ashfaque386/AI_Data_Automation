"""
Connection Profile Model - Stores User Operational Database configurations
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class ConnectionProfile(Base):
    """User Operational Database connection profile."""
    __tablename__ = "connection_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Database type: postgresql, mysql, oracle, mssql, sqlite, duckdb
    db_type = Column(String(50), nullable=False)
    
    # Connection details
    host = Column(String(255), nullable=True)  # Nullable for sqlite/duckdb
    port = Column(Integer, nullable=True)
    database = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=True)  # Encrypted at rest
    schema = Column(String(255), nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=False, nullable=False)
    is_read_only = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)  # User ID
    
    def get_connection_string(self, decrypted_password: str = None) -> str:
        """Generate connection string from profile."""
        if self.db_type == "postgresql":
            password = decrypted_password or ""
            return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "mysql":
            password = decrypted_password or ""
            return f"mysql+pymysql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == "sqlite":
            return f"sqlite:///{self.database}"
        elif self.db_type == "duckdb":
            return f"duckdb:///{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
