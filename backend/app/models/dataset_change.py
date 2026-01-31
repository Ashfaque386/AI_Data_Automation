from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DatasetChange(Base):
    """
    Tracks all changes made to datasets during edit sessions.
    Provides comprehensive audit trail for data modifications.
    """
    __tablename__ = "dataset_changes"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Change metadata
    change_type = Column(String(50), nullable=False)  # cell_edit, row_add, row_delete, column_add, etc.
    row_index = Column(Integer, nullable=True)  # For row-level operations
    column_name = Column(String(255), nullable=True)  # For cell/column operations
    
    # Change data
    old_value = Column(JSON, nullable=True)  # Previous value (for undo)
    new_value = Column(JSON, nullable=True)  # New value
    
    # Session tracking
    session_id = Column(String(36), nullable=False, index=True)  # UUID for grouping changes
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_committed = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="changes")
    user = relationship("User")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_dataset_session', 'dataset_id', 'session_id'),
        Index('idx_session_committed', 'session_id', 'is_committed'),
        Index('idx_dataset_timestamp', 'dataset_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<DatasetChange(id={self.id}, type={self.change_type}, session={self.session_id})>"
