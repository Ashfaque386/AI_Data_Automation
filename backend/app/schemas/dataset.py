"""
Dataset Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


class DatasetStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class ColumnType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


class DatasetColumnBase(BaseModel):
    name: str
    data_type: ColumnType = ColumnType.STRING
    nullable: bool = True


class DatasetColumnCreate(DatasetColumnBase):
    original_name: Optional[str] = None
    position: Optional[int] = None
    formula: Optional[str] = None


class DatasetColumnResponse(DatasetColumnBase):
    id: int
    original_name: Optional[str] = None
    position: int
    unique_count: Optional[int] = None
    null_count: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    avg_value: Optional[str] = None
    sample_values: Optional[List[Any]] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_calculated: bool = False
    formula: Optional[str] = None
    
    class Config:
        from_attributes = True


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_locked: Optional[bool] = None


class DatasetResponse(DatasetBase):
    id: int
    source_type: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    row_count: Optional[int] = None
    status: DatasetStatus
    error_message: Optional[str] = None
    virtual_table_name: Optional[str] = None
    owner_id: int
    is_public: bool
    is_locked: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    columns: List[DatasetColumnResponse] = []
    
    class Config:
        from_attributes = True


class DatasetVersionResponse(BaseModel):
    id: int
    version_number: int
    change_type: Optional[str] = None
    change_summary: Optional[str] = None
    row_count: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    file_type: Optional[str] = None
    row_count: Optional[int] = None
    status: DatasetStatus
    owner_id: int
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UploadConfig(BaseModel):
    """Configuration for file upload."""
    encoding: str = "utf-8"
    delimiter: Optional[str] = None
    has_header: bool = True
    sheet_name: Optional[str] = None
    skip_rows: int = 0
    column_types: Optional[Dict[str, ColumnType]] = None


class DataGridRequest(BaseModel):
    """Request for paginated data grid."""
    page: int = 1
    page_size: int = 100
    sort_by: Optional[str] = None
    sort_desc: bool = False
    filters: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None


class DataGridResponse(BaseModel):
    """Response for paginated data grid."""
    data: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    columns: List[DatasetColumnResponse]


class CellUpdate(BaseModel):
    """Single cell update."""
    row_id: int
    column: str
    value: Any


class BulkUpdateRequest(BaseModel):
    """Bulk cell updates."""
    updates: List[CellUpdate]


class ColumnStats(BaseModel):
    """Column statistics."""
    column_name: str
    data_type: str
    total_count: int
    unique_count: int
    null_count: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    sample_values: List[Any] = []
