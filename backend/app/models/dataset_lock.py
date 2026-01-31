from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DatasetLock(Base):
    """
    Manages exclusive locks on datasets during edit sessions.
    Prevents concurrent edits and ensures data consistency.
    """
    __tablename__ = "dataset_locks"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Lock metadata
    session_id = Column(String(36), nullable=False, unique=True)  # UUID for this edit session
    locked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Auto-release after timeout
    
    # Relationships
    dataset = relationship("Dataset", back_populates="lock")
    user = relationship("User")

    def __repr__(self):
        return f"<DatasetLock(dataset_id={self.dataset_id}, user_id={self.user_id}, session={self.session_id})>"
    
    @property
    def is_expired(self):
        """Check if lock has expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at
