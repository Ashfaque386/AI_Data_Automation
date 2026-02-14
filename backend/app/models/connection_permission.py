"""
Connection Permission Model - Per-connection RBAC
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class ConnectionPermission(Base):
    """Per-connection access control."""
    __tablename__ = "connection_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connection_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Permission target (either user OR role, not both)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Permissions
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)
    can_execute_ddl = Column(Boolean, default=False, nullable=False)
    
    # Schema/Table restrictions (PostgreSQL ARRAY type)
    allowed_schemas = Column(ARRAY(String), nullable=True)  # NULL = all schemas
    denied_tables = Column(ARRAY(String), nullable=True)   # NULL = no restrictions
    
    # Relationships
    connection = relationship("ConnectionProfile", backref="permissions")
    user = relationship("User", backref="connection_permissions")
    role = relationship("Role", backref="connection_permissions")
