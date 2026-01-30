"""
Dataset, Version, and Column Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, BigInteger, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class DatasetStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class ColumnType(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    BINARY = "binary"


class Dataset(Base):
    """Dataset model representing uploaded data."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    source_type = Column(String(50))  # 'file', 'database', 'api'
    source_path = Column(String(500))
    file_type = Column(String(20))  # 'xlsx', 'csv', 'json', etc.
    file_size = Column(BigInteger)
    row_count = Column(BigInteger)
    status = Column(String(20), default=DatasetStatus.UPLOADING.value)
    error_message = Column(Text)
    
    # Metadata
    encoding = Column(String(50), default='utf-8')
    delimiter = Column(String(10))
    has_header = Column(Boolean, default=True)
    sheet_name = Column(String(100))  # For Excel files
    
    # Virtual table name in DuckDB
    virtual_table_name = Column(String(255), unique=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_public = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="datasets")
    columns = relationship("DatasetColumn", back_populates="dataset", cascade="all, delete-orphan")
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    permissions = relationship("DatasetPermission", back_populates="dataset", cascade="all, delete-orphan")


class DatasetColumn(Base):
    """Column metadata for a dataset."""
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255))
    data_type = Column(String(50), default=ColumnType.STRING.value)
    nullable = Column(Boolean, default=True)
    position = Column(Integer)
    
    # Statistics
    unique_count = Column(BigInteger)
    null_count = Column(BigInteger)
    min_value = Column(String(500))
    max_value = Column(String(500))
    avg_value = Column(String(500))
    sample_values = Column(JSON)
    
    # Constraints
    is_primary_key = Column(Boolean, default=False)
    is_unique = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    
    # Formula support
    is_calculated = Column(Boolean, default=False)
    formula = Column(Text)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="columns")


class DatasetVersion(Base):
    """Version history for datasets."""
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)
    snapshot_path = Column(String(500))  # Path to versioned data file
    
    # Change tracking
    change_type = Column(String(50))  # 'upload', 'edit', 'transform', 'import'
    change_summary = Column(Text)
    changed_by_id = Column(Integer, ForeignKey('users.id'))
    row_count = Column(BigInteger)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    dataset = relationship("Dataset", back_populates="versions")


class DatasetPermission(Base):
    """Column-level and dataset-level permissions."""
    __tablename__ = "dataset_permissions"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'))
    
    # Permission level
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    can_export = Column(Boolean, default=False)
    
    # Column-level restrictions (JSON list of column names)
    visible_columns = Column(JSON)  # null = all columns visible
    editable_columns = Column(JSON)  # null = all columns editable (if can_write)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="permissions")
