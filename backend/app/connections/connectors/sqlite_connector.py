"""
SQLite Database Connector
"""
from typing import Any, Dict, List, Optional
import time
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
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


class SQLiteConnector(BaseConnector):
    """SQLite database connector implementation."""
    
    def connect(self) -> None:
        """Establish connection to SQLite database."""
        try:
            self._engine = create_engine(
                self.connection_string,
                connect_args={'timeout': self.timeout}
            )
            self._connection = self._engine.connect()
            self._inspector = inspect(self._engine)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {str(e)}")
    
    def disconnect(self) -> None:
        """Close SQLite connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._engine:
            self._engine.dispose()
            self._engine = None
    
    def test_connection(self) -> HealthCheckResult:
        """Test SQLite connection health."""
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
        """Execute SQL query on SQLite."""
        start_time = time.time()
        try:
            if params:
                result = self._connection.execute(text(sql), params)
            else:
                result = self._connection.execute(text(sql))
            
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
        """List databases (SQLite only has main)."""
        return ["main"]
    
    def list_schemas(self) -> List[str]:
        """List all SQLite schemas (always returns ['main'])."""
        return ['main']
    
    def list_tables(self, schema: str = 'main') -> List[TableInfo]:
        """List all tables in SQLite database."""
        tables = []
        for table_name in self._inspector.get_table_names():
            tables.append(TableInfo(
                name=table_name,
                schema='main',
                table_type="table"
            ))
        
        # Add views
        for view_name in self._inspector.get_view_names():
            tables.append(TableInfo(
                name=view_name,
                schema='main',
                table_type="view"
            ))
        
        return tables
    
    def get_table_schema(self, table: str, schema: str = 'main') -> TableSchema:
        """Get complete table schema."""
        columns = []
        for col in self._inspector.get_columns(table):
            columns.append(ColumnInfo(
                name=col['name'],
                data_type=str(col['type']),
                is_nullable=col['nullable'],
                default_value=str(col['default']) if col['default'] else None
            ))
        
        pk_constraint = self._inspector.get_pk_constraint(table)
        primary_keys = pk_constraint.get('constrained_columns', [])
        
        foreign_keys = self._inspector.get_foreign_keys(table)
        indexes = self._inspector.get_indexes(table)
        
        return TableSchema(
            table_name=table,
            schema_name='main',
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
        """Detect SQLite capabilities."""
        # Get version
        version_result = self._connection.execute(text("SELECT sqlite_version()"))
        version = version_result.fetchone()[0]
        
        return DatabaseCapabilities(
            version=f"SQLite {version}",
            supports_transactions=True,
            supports_stored_procedures=False,  # SQLite doesn't support stored procedures
            supports_views=True,
            supports_materialized_views=False,
            supports_json=True,  # SQLite 3.9+ supports JSON
            supports_full_text_search=True,  # FTS5 extension
            max_connections=1,  # SQLite is single-connection
            features=["ACID", "Triggers", "Views", "JSON", "Full Text Search (FTS5)"],
            extensions=[]
        )
