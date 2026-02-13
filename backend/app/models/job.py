"""
Job and Scheduler Models - Enterprise Grade
Supports SQL scripts, stored procedures, database backups, and advanced scheduling
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class JobType(str, enum.Enum):
    """Job type enumeration"""
    SQL_QUERY = "sql_query"
    SQL_SCRIPT = "sql_script"
    STORED_PROCEDURE = "stored_procedure"
    DATABASE_BACKUP = "database_backup"
    DATA_IMPORT = "data_import"
    DATA_EXPORT = "data_export"
    DATA_SYNC = "data_sync"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"


class JobStatus(str, enum.Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class BackupType(str, enum.Enum):
    """Database backup types"""
    FULL = "full"
    SCHEMA_ONLY = "schema_only"
    DATA_ONLY = "data_only"


class ScheduledJob(Base):
    """Scheduled job configuration with enterprise features."""
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    job_type = Column(String(50), nullable=False)
    
    # Target connection (User Operational DB only)
    connection_id = Column(Integer, ForeignKey('connection_profiles.id', ondelete='CASCADE'))
    target_schema = Column(String(255))
    
    # Schedule configuration
    cron_expression = Column(String(100))
    timezone = Column(String(50), default='UTC')
    is_active = Column(Boolean, default=True)
    
    # Job-specific configuration
    config = Column(JSON, nullable=False)  # SQL script, procedure name, backup settings, etc.
    
    # Execution hooks
    pre_execution_sql = Column(Text)  # Optional SQL to run before job
    post_execution_sql = Column(Text)  # Optional SQL to run after job
    
    # Retry policy
    retry_policy = Column(JSON)  # {max_retries: 3, backoff_multiplier: 2, max_backoff_seconds: 300}
    max_runtime_seconds = Column(Integer, default=3600)  # 1 hour default
    failure_threshold = Column(Integer, default=5)  # Auto-disable after N consecutive failures
    
    # Target dataset (for data import jobs)
    target_dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'))
    
    # Notification settings
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_emails = Column(JSON)
    notification_webhook = Column(String(500))
    
    # Ownership and permissions
    created_by_id = Column(Integer, ForeignKey('users.id'))
    requires_approval = Column(Boolean, default=False)
    
    # Statistics
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")
    parameters = relationship("JobParameter", back_populates="job", cascade="all, delete-orphan")
    connection = relationship("ConnectionProfile")


class JobExecution(Base):
    """Job execution history with detailed logging."""
    __tablename__ = "job_executions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False)
    
    # Execution info
    status = Column(String(20), default=JobStatus.PENDING.value)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    
    # Results
    result = Column(JSON)  # Query results, backup metadata, etc.
    rows_processed = Column(Integer)
    rows_affected = Column(Integer)
    error_message = Column(Text)
    error_stack_trace = Column(Text)
    
    # Detailed logging
    execution_logs = Column(Text)  # Detailed execution logs
    
    # Resource usage
    resource_usage = Column(JSON)  # {memory_mb: 128, cpu_percent: 45, disk_io_mb: 256}
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    is_retry = Column(Boolean, default=False)
    parent_execution_id = Column(Integer, ForeignKey('job_executions.id', ondelete='SET NULL'))
    
    # Triggered by
    triggered_by = Column(String(50))  # 'schedule', 'manual', 'api', 'retry'
    triggered_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("ScheduledJob", back_populates="executions")
    triggered_by_user = relationship("User")


class JobParameter(Base):
    """Parameters for stored procedure jobs."""
    __tablename__ = "job_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('scheduled_jobs.id', ondelete='CASCADE'), nullable=False)
    
    # Parameter definition
    parameter_name = Column(String(255), nullable=False)
    parameter_type = Column(String(100), nullable=False)  # INTEGER, VARCHAR, etc.
    parameter_mode = Column(String(20), default='IN')  # IN, OUT, INOUT
    parameter_order = Column(Integer, default=0)
    
    # Parameter value
    default_value = Column(Text)
    is_required = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job = relationship("ScheduledJob", back_populates="parameters")


class BackupConfiguration(Base):
    """Database backup configuration and history."""
    __tablename__ = "backup_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('scheduled_jobs.id', ondelete='CASCADE'))
    execution_id = Column(Integer, ForeignKey('job_executions.id', ondelete='SET NULL'))
    
    # Backup details
    backup_type = Column(String(50), nullable=False)  # full, schema_only, data_only
    backup_format = Column(String(50), default='custom')  # custom, plain, tar, directory
    compression_enabled = Column(Boolean, default=True)
    compression_level = Column(Integer, default=6)  # 0-9 for gzip
    
    # Storage
    storage_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer)
    
    # Database info
    database_name = Column(String(255), nullable=False)
    database_type = Column(String(50), nullable=False)  # postgresql, mysql
    
    # Backup metadata
    backup_started_at = Column(DateTime(timezone=True))
    backup_completed_at = Column(DateTime(timezone=True))
    backup_duration_seconds = Column(Integer)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(50))
    checksum = Column(String(128))
    
    # Retention
    retention_days = Column(Integer, default=30)
    expires_at = Column(DateTime(timezone=True))
    
    # Ownership
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    created_by = relationship("User")
