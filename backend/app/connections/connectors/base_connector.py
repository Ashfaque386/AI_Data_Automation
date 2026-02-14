"""
Base Connector Interface for Multi-Database Support
All database connectors must implement this interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import enum


class QueryResultStatus(str, enum.Enum):
    """Query execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TableInfo:
    """Table metadata."""
    name: str
    schema: str
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    table_type: str = "table"  # table, view, materialized_view


@dataclass
class ColumnInfo:
    """Column metadata."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


@dataclass
class TableSchema:
    """Complete table schema."""
    table_name: str
    schema_name: str
    columns: List[ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]


@dataclass
class QueryResult:
    """Query execution result."""
    status: QueryResultStatus
    rows: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time_ms: int
    error_message: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Health check result."""
    is_healthy: bool
    response_time_ms: int
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class DatabaseCapabilities:
    """Database capabilities and features."""
    version: str
    supports_transactions: bool
    supports_stored_procedures: bool
    supports_views: bool
    supports_materialized_views: bool
    supports_json: bool
    supports_full_text_search: bool
    max_connections: int
    features: List[str]
    extensions: List[str]


class BaseConnector(ABC):
    """
    Abstract base class for database connectors.
    
    All database-specific connectors must implement this interface.
    """
    
    def __init__(self, connection_string: str, pool_size: int = 5, timeout: int = 30):
        """
        Initialize connector.
        
        Args:
            connection_string: Database connection string
            pool_size: Connection pool size
            timeout: Connection timeout in seconds
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.timeout = timeout
        self._connection = None
        self._pool = None
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to database.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        pass
    
    @abstractmethod
    def test_connection(self) -> HealthCheckResult:
        """
        Test database connection health.
        
        Returns:
            HealthCheckResult with status and response time
        """
        pass
    
    @abstractmethod
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query string
            params: Query parameters (optional)
            
        Returns:
            QueryResult with rows and metadata
        """
        pass
    
    @abstractmethod
    def execute_ddl(self, sql: str) -> bool:
        """
        Execute DDL statement (CREATE, ALTER, DROP).
        
        Args:
            sql: DDL statement
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def list_databases(self) -> List[str]:
        """
        List all available databases on the server.
        
        Returns:
            List of database names
        """
        pass

    @abstractmethod
    def list_schemas(self) -> List[str]:
        """
        List all schemas/databases.
        
        Returns:
            List of schema names
        """
        pass
    
    @abstractmethod
    def list_tables(self, schema: str) -> List[TableInfo]:
        """
        List all tables in a schema.
        
        Args:
            schema: Schema name
            
        Returns:
            List of TableInfo objects
        """
        pass
    
    @abstractmethod
    def get_table_schema(self, table: str, schema: str) -> TableSchema:
        """
        Get complete table schema.
        
        Args:
            table: Table name
            schema: Schema name
            
        Returns:
            TableSchema with columns and constraints
        """
        pass
    
    @abstractmethod
    def start_transaction(self) -> None:
        """Begin a new transaction."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Commit current transaction."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Rollback current transaction."""
        pass
    
    @abstractmethod
    def detect_capabilities(self) -> DatabaseCapabilities:
        """
        Detect database capabilities and features.
        
        Returns:
            DatabaseCapabilities with version and features
        """
        pass
    
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connection is not None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.rollback()
        self.disconnect()
