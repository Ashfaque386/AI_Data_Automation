"""
Connection Health Log Model - Tracks connection health history
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ConnectionHealthLog(Base):
    """Log of connection health checks."""
    __tablename__ = "connection_health_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connection_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Health check results
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    status = Column(String(20), nullable=False)  # online, offline, degraded
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Who triggered the check
    checked_by = Column(String(50), nullable=False, default="system")  # system, user, scheduler
    
    # Relationship
    connection = relationship("ConnectionProfile", backref="health_logs")
