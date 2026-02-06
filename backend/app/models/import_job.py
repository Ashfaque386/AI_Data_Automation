"""
Import Job Models
Tracks data import operations from datasets to database tables
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ImportJob(Base):
    """Tracks import job execution and results"""
    __tablename__ = "import_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    target_connection_id = Column(Integer, ForeignKey("connection_profiles.id"), nullable=False)
    target_table = Column(String(255), nullable=False)
    target_schema = Column(String(255), default="public")
    
    # Status tracking
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    import_mode = Column(String(50), nullable=False)  # insert, upsert, truncate_insert
    
    # Progress metrics
    total_rows = Column(Integer)
    inserted_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    
    # Configuration
    mapping_config = Column(JSON)  # Column mappings
    import_config = Column(JSON)   # Batch size, constraints, etc.
    
    # Error tracking
    error_details = Column(JSON)   # Error messages and failed rows
    error_message = Column(Text)   # Summary error message
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="import_jobs")
    dataset = relationship("Dataset")
    connection = relationship("ConnectionProfile")
    audit_logs = relationship("ImportAuditLog", back_populates="import_job", cascade="all, delete-orphan")


class ImportMapping(Base):
    """Saved column mapping templates"""
    __tablename__ = "import_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Mapping details
    source_type = Column(String(50))  # csv, excel, json
    target_table = Column(String(255))
    target_schema = Column(String(255), default="public")
    mapping_config = Column(JSON, nullable=False)
    
    # Metadata
    is_shared = Column(Integer, default=0)  # 0=private, 1=shared
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


class ImportAuditLog(Base):
    """Audit trail for import operations"""
    __tablename__ = "import_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    action = Column(String(100), nullable=False)  # started, validated, executed, failed, cancelled
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    import_job = relationship("ImportJob", back_populates="audit_logs")
    user = relationship("User")
