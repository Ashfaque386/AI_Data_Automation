"""
Audit Log Model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    """Audit log for tracking all operations."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Actor
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    user_email = Column(String(255))  # Denormalized for historical tracking
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    
    # Action
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), index=True)  # 'dataset', 'user', 'query', etc.
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
