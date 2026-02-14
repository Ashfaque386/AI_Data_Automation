"""
Audit Log Model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class AuditActionType(str, enum.Enum):
    """Types of auditable actions"""
    # Connection Management
    CONNECTION_CREATE = "connection_create"
    CONNECTION_UPDATE = "connection_update"
    CONNECTION_DELETE = "connection_delete"
    CONNECTION_ACTIVATE = "connection_activate"
    CONNECTION_DEACTIVATE = "connection_deactivate"
    CONNECTION_TEST = "connection_test"
    
    # Query Operations
    QUERY_EXECUTE = "query_execute"
    QUERY_EXPLAIN = "query_explain"
    
    # Schema Operations
    SCHEMA_LIST = "schema_list"
    SCHEMA_ACCESS = "schema_access"
    TABLE_LIST = "table_list"
    TABLE_ACCESS = "table_access"
    TABLE_CREATE = "table_create"
    TABLE_DROP = "table_drop"
    
    # Permission Management
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    PERMISSION_VIEW = "permission_view"
    
    # Data Operations
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    DATA_INSERT = "data_insert"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    
    # Health & Monitoring
    HEALTH_CHECK = "health_check"
    CAPABILITY_DETECT = "capability_detect"
    
    # Authentication
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"


class AuditLog(Base):
    """Audit log for tracking all operations."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Actor
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    user_email = Column(String(255))  # Denormalized for historical tracking
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    # Connection context
    connection_id = Column(Integer, ForeignKey('connection_profiles.id', ondelete='SET NULL'), nullable=True, index=True)
    connection_name = Column(String(255))  # Denormalized
    
    # Action
    action = Column(String(100), nullable=False, index=True)  # For backward compatibility
    action_type = Column(SQLEnum(AuditActionType), nullable=True, index=True)  # New structured field
    resource_type = Column(String(100), index=True)  # 'dataset', 'user', 'query', 'connection', etc.
    resource_id = Column(String(100))
    resource_name = Column(String(255))
    
    # Details
    details = Column(JSON)
    query_text = Column(Text)  # For SQL queries
    
    # Status
    status = Column(String(20), default='success')  # 'success', 'failure', 'warning'
    error_message = Column(Text)
    
    # Performance
    duration_ms = Column(Integer)
    rows_affected = Column(Integer)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    connection = relationship("ConnectionProfile", foreign_keys=[connection_id])


class QueryHistory(Base):
    """SQL query history for versioning and replay."""
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    # Query info
    name = Column(String(255))
    query_text = Column(Text, nullable=False)
    query_hash = Column(String(64), index=True)  # For deduplication
    
    # Execution stats
    execution_count = Column(Integer, default=1)
    last_executed_at = Column(DateTime(timezone=True))
    avg_duration_ms = Column(Integer)
    
    # Flags
    is_saved = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TableEntryAudit(Base):
    """Audit log for table entry operations."""
    __tablename__ = "table_entry_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("connection_profiles.id"), nullable=False)
    target_schema = Column(String(255), nullable=False)
    target_table = Column(String(255), nullable=False)
    rows_attempted = Column(Integer, nullable=False)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_failed = Column(Integer, nullable=False, default=0)
    insert_mode = Column(String(50), nullable=False)  # transaction, row-by-row
    error_details = Column(JSON)  # List of error details for failed rows
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    connection = relationship("ConnectionProfile")

