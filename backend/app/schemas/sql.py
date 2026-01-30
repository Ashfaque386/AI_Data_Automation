"""
SQL Execution Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


class QueryType(str, Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"


class SQLRequest(BaseModel):
    """SQL query execution request."""
    query: str = Field(..., min_length=1)
    limit: Optional[int] = Field(default=1000, le=100000)
    timeout_seconds: Optional[int] = Field(default=30, le=300)
    explain: bool = False
    source: str = Field(default="duckdb", description="Execution engine: 'duckdb' or 'postgres'")


class SQLResultColumn(BaseModel):
    """Column info in SQL result."""
    name: str
    data_type: str


class SQLResult(BaseModel):
    """SQL query execution result."""
    success: bool
    query: str
    query_type: QueryType
    columns: List[SQLResultColumn] = []
    data: List[Dict[str, Any]] = []
    row_count: int = 0
    rows_affected: int = 0
    execution_time_ms: int
    error_message: Optional[str] = None
    warnings: List[str] = []


class QueryPlan(BaseModel):
    """Query execution plan."""
    plan_text: str
    estimated_cost: Optional[float] = None
    estimated_rows: Optional[int] = None


class QueryExplainResult(BaseModel):
    """Explain query result."""
    query: str
    plan: QueryPlan
    recommendations: List[str] = []


class SavedQuery(BaseModel):
    """Saved query request."""
    name: str = Field(..., min_length=1, max_length=255)
    query: str
    description: Optional[str] = None


class QueryHistoryItem(BaseModel):
    """Query history item."""
    id: int
    query_text: str
    name: Optional[str] = None
    execution_count: int
    last_executed_at: Optional[datetime] = None
    avg_duration_ms: Optional[int] = None
    is_saved: bool
    is_favorite: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class NoCodeJoin(BaseModel):
    """No-code join configuration."""
    left_dataset: str
    right_dataset: str
    left_column: str
    right_column: str
    join_type: str = "inner"  # inner, left, right, outer


class NoCodeFilter(BaseModel):
    """No-code filter configuration."""
    column: str
    operator: str  # eq, neq, gt, gte, lt, lte, like, in, notnull, isnull
    value: Any


class NoCodeAggregation(BaseModel):
    """No-code aggregation configuration."""
    column: str
    function: str  # sum, avg, count, min, max, distinct_count


class NoCodeQueryRequest(BaseModel):
    """No-code query builder request."""
    datasets: List[str]
    columns: List[str]
    joins: List[NoCodeJoin] = []
    filters: List[NoCodeFilter] = []
    aggregations: List[NoCodeAggregation] = []
    group_by: List[str] = []
    order_by: Optional[str] = None
    order_desc: bool = False
    limit: int = 1000
