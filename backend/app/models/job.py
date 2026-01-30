"""
Job and Scheduler Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class JobType(str, enum.Enum):
    SQL_QUERY = "sql_query"
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    DATA_SYNC = "data_sync"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledJob(Base):
    """Scheduled job configuration."""
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    job_type = Column(String(50), nullable=False)
    
    # Schedule (cron expression)
    cron_expression = Column(String(100))
    is_active = Column(Boolean, default=True)
    
    # Configuration
    config = Column(JSON, nullable=False)  # Job-specific configuration
    
    # Target
    target_dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'))
    
    # Notification
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_emails = Column(JSON)
    
    # Ownership
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Stats
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    run_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")


class JobExecution(Base):
    """Job execution history."""
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False)
    
    # Execution info
    status = Column(String(20), default=JobStatus.PENDING.value)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    
    # Results
    result = Column(JSON)
    rows_processed = Column(Integer)
    error_message = Column(Text)
    
    # Triggered by
    triggered_by = Column(String(50))  # 'schedule', 'manual', 'api'
    triggered_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("ScheduledJob", back_populates="executions")
