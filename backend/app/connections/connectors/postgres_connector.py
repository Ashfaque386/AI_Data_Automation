"""
PostgreSQL Database Connector
"""
from typing import Any, Dict, List, Optional
import time
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from app.connections.connectors.base_connector import (
    BaseConnector,
    QueryResult,
    QueryResultStatus,
    HealthCheckResult,
    TableInfo,
    ColumnInfo,
    TableSchema,
    DatabaseCapabilities
)


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector implementation."""
    
    def connect(self) -> None:
        """Establish connection to PostgreSQL database."""
        try:
            self._engine = create_engine(
                self.connection_string,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.pool_size * 2,
                pool_pre_ping=True,
                connect_args={'connect_timeout': self.timeout}
            )
            self._connection = self._engine.connect()
            self._inspector = inspect(self._engine)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._engine:
            self._engine.dispose()
            self._engine = None
    
    def test_connection(self) -> HealthCheckResult:
        """Test PostgreSQL connection health."""
        start_time = time.time()
        try:
            if not self._connection:
                self.connect()
            
            result = self._connection.execute(text("SELECT 1"))
            result.close()
            
            response_time_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                is_healthy=True,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Execute SQL query on PostgreSQL."""
        start_time = time.time()
        try:
            if params:
                result = self._connection.execute(text(sql), params)
            else:
                result = self._connection.execute(text(sql))
            
            # Fetch results
            rows = []
            columns = []
            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(row._mapping) for row in result]
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return QueryResult(
                status=QueryResultStatus.SUCCESS,
                rows=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time_ms
            )
        except SQLAlchemyError as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return QueryResult(
                status=QueryResultStatus.ERROR,
                rows=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error_message=str(e)
            )
    
    def execute_ddl(self, sql: str) -> bool:
        """Execute DDL statement."""
        try:
            self._connection.execute(text(sql))
            self._connection.commit()
            return True
        except SQLAlchemyError:
            self._connection.rollback()
            return False
            
    def list_databases(self) -> List[str]:
        """List all PostgreSQL databases."""
        result = self._connection.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false"))
        return [row[0] for row in result]
    
    def list_schemas(self) -> List[str]:
        """List all PostgreSQL schemas."""
        return self._inspector.get_schema_names()
    
    def list_tables(self, schema: str) -> List[TableInfo]:
        """List all tables in a schema."""
        tables = []
        for table_name in self._inspector.get_table_names(schema=schema):
            tables.append(TableInfo(
                name=table_name,
                schema=schema,
                table_type="table"
            ))
        
        # Add views
        for view_name in self._inspector.get_view_names(schema=schema):
            tables.append(TableInfo(
                name=view_name,
                schema=schema,
                table_type="view"
            ))
        
        return tables
    
    def get_table_schema(self, table: str, schema: str) -> TableSchema:
        """Get complete table schema."""
        columns = []
        for col in self._inspector.get_columns(table, schema=schema):
            columns.append(ColumnInfo(
                name=col['name'],
                data_type=str(col['type']),
                is_nullable=col['nullable'],
                default_value=str(col['default']) if col['default'] else None
            ))
        
        # Get primary keys
        pk_constraint = self._inspector.get_pk_constraint(table, schema=schema)
        primary_keys = pk_constraint.get('constrained_columns', [])
        
        # Get foreign keys
        foreign_keys = self._inspector.get_foreign_keys(table, schema=schema)
        
        # Get indexes
        indexes = self._inspector.get_indexes(table, schema=schema)
        
        return TableSchema(
            table_name=table,
            schema_name=schema,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes
        )
    
    def start_transaction(self) -> None:
        """Begin a new transaction."""
        self._connection.execute(text("BEGIN"))
    
    def commit(self) -> None:
        """Commit current transaction."""
        self._connection.commit()
    
    def rollback(self) -> None:
        """Rollback current transaction."""
        self._connection.rollback()
    
    def detect_capabilities(self) -> DatabaseCapabilities:
        """Detect PostgreSQL capabilities."""
        # Get version
        version_result = self._connection.execute(text("SELECT version()"))
        version_row = version_result.fetchone()
        version = version_row[0] if version_row else "Unknown"
        
        # Get extensions
        extensions_result = self._connection.execute(text("SELECT extname FROM pg_extension"))
        extensions = [row[0] for row in extensions_result]
        
        # Get max connections
        max_conn_result = self._connection.execute(text("SHOW max_connections"))
        max_connections = int(max_conn_result.fetchone()[0])
        
        return DatabaseCapabilities(
            version=version,
            supports_transactions=True,
            supports_stored_procedures=True,
            supports_views=True,
            supports_materialized_views=True,
            supports_json=True,
            supports_full_text_search=True,
            max_connections=max_connections,
            features=["ACID", "Foreign Keys", "Triggers", "Stored Procedures", "JSON", "Full Text Search"],
            extensions=extensions
        )
