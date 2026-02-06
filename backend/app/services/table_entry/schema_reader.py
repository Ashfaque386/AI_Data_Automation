"""
Schema Reader Service
Fetches table metadata, constraints, and statistics from user operational databases.
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import structlog

from app.models import ConnectionProfile
from app.database import get_db

logger = structlog.get_logger()


class SchemaReader:
    """Service for reading database schema metadata."""
    
    def __init__(self, connection_profile: ConnectionProfile):
        """Initialize with a connection profile."""
        self.connection_profile = connection_profile
        self.engine = self._create_engine()
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine from connection profile."""
        from app.core.crypto import decrypt_value
        
        # Decrypt password
        password = decrypt_value(self.connection_profile.encrypted_password)
        
        # Build connection URL
        if self.connection_profile.db_type == "postgresql":
            url = f"postgresql://{self.connection_profile.username}:{password}@{self.connection_profile.host}:{self.connection_profile.port}/{self.connection_profile.database}"
        elif self.connection_profile.db_type == "mysql":
            url = f"mysql+pymysql://{self.connection_profile.username}:{password}@{self.connection_profile.host}:{self.connection_profile.port}/{self.connection_profile.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.connection_profile.db_type}")
        
        return create_engine(url, pool_pre_ping=True)
    
    def get_schemas(self) -> List[str]:
        """Get list of schemas in the database."""
        try:
            inspector = inspect(self.engine)
            schemas = inspector.get_schema_names()
            
            # Filter out system schemas
            if self.connection_profile.db_type == "postgresql":
                schemas = [s for s in schemas if s not in ('information_schema', 'pg_catalog', 'pg_toast')]
            elif self.connection_profile.db_type == "mysql":
                schemas = [s for s in schemas if s not in ('information_schema', 'mysql', 'performance_schema', 'sys')]
            
            return sorted(schemas)
        except Exception as e:
            logger.error(f"Failed to get schemas: {str(e)}")
            raise
    
    def get_tables(self, schema: str) -> List[Dict[str, Any]]:
        """Get list of tables in a schema with metadata."""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names(schema=schema)
            
            result = []
            for table in tables:
                # Get row count
                try:
                    with self.engine.connect() as conn:
                        count_query = text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                        row_count = conn.execute(count_query).scalar()
                except:
                    row_count = None
                
                result.append({
                    "name": table,
                    "schema": schema,
                    "row_count": row_count
                })
            
            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            logger.error(f"Failed to get tables for schema {schema}: {str(e)}")
            raise
    
    def get_table_schema(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get detailed column information for a table."""
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table, schema=schema)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table, schema=schema)
            pk_columns = pk_constraint.get('constrained_columns', []) if pk_constraint else []
            
            # Get foreign keys
            fk_constraints = inspector.get_foreign_keys(table, schema=schema)
            fk_columns = {}
            for fk in fk_constraints:
                for col in fk.get('constrained_columns', []):
                    fk_columns[col] = {
                        'referenced_table': fk.get('referred_table'),
                        'referenced_column': fk.get('referred_columns', [])[0] if fk.get('referred_columns') else None
                    }
            
            # Get unique constraints
            unique_constraints = inspector.get_unique_constraints(table, schema=schema)
            unique_columns = set()
            for uc in unique_constraints:
                for col in uc.get('column_names', []):
                    unique_columns.add(col)
            
            # Build column metadata
            result = []
            for col in columns:
                col_info = {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': str(col['default']) if col['default'] is not None else None,
                    'is_primary_key': col['name'] in pk_columns,
                    'is_foreign_key': col['name'] in fk_columns,
                    'foreign_key_ref': fk_columns.get(col['name']),
                    'is_unique': col['name'] in unique_columns,
                    'autoincrement': col.get('autoincrement', False)
                }
                result.append(col_info)
            
            return result
        except Exception as e:
            logger.error(f"Failed to get schema for {schema}.{table}: {str(e)}")
            raise
    
    def get_table_constraints(self, schema: str, table: str) -> Dict[str, Any]:
        """Get all constraints for a table."""
        try:
            inspector = inspect(self.engine)
            
            return {
                'primary_key': inspector.get_pk_constraint(table, schema=schema),
                'foreign_keys': inspector.get_foreign_keys(table, schema=schema),
                'unique_constraints': inspector.get_unique_constraints(table, schema=schema),
                'check_constraints': inspector.get_check_constraints(table, schema=schema)
            }
        except Exception as e:
            logger.error(f"Failed to get constraints for {schema}.{table}: {str(e)}")
            raise
    
    def get_table_stats(self, schema: str, table: str) -> Dict[str, Any]:
        """Get table statistics."""
        try:
            with self.engine.connect() as conn:
                # Get row count
                count_query = text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                row_count = conn.execute(count_query).scalar()
                
                # Check insert permissions (try to prepare an INSERT statement)
                has_insert_permission = True
                try:
                    # This is a dry run - we don't actually insert
                    inspector = inspect(self.engine)
                    columns = inspector.get_columns(table, schema=schema)
                    if columns:
                        # Just check if we can prepare the statement
                        col_name = columns[0]['name']
                        test_query = text(f'SELECT 1 FROM "{schema}"."{table}" WHERE 1=0')
                        conn.execute(test_query)
                except:
                    has_insert_permission = False
                
                return {
                    'row_count': row_count,
                    'has_insert_permission': has_insert_permission
                }
        except Exception as e:
            logger.error(f"Failed to get stats for {schema}.{table}: {str(e)}")
            raise
    
    
    def get_foreign_key_values(self, schema: str, table: str, column: str, search_query: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch potential values for a foreign key column from the referenced table."""
        try:
            inspector = inspect(self.engine)
            fk_constraints = inspector.get_foreign_keys(table, schema=schema)
            
            # Find the FK constraint for this column
            target_fk = None
            for fk in fk_constraints:
                if column in fk.get('constrained_columns', []):
                    target_fk = fk
                    break
            
            if not target_fk:
                raise ValueError(f"Column {column} is not a foreign key")
            
            ref_table = target_fk['referred_table']
            # Find the referenced column (index matches constrained column index)
            col_idx = target_fk['constrained_columns'].index(column)
            ref_col = target_fk['referred_columns'][col_idx]
            ref_schema = target_fk.get('referred_schema', schema)
            
            # Build query to fetch values
            with self.engine.connect() as conn:
                # Select the referenced column and try to find a meaningful label (e.g. name, title)
                # For now, just selecting the ID
                query_str = f'SELECT "{ref_col}" FROM "{ref_schema}"."{ref_table}"'
                
                if search_query:
                    # Basic search integration if needed
                    # Note: Type casting might be needed for non-string columns
                    query_str += f' WHERE CAST("{ref_col}" AS TEXT) LIKE :search'
                
                query_str += f' ORDER BY "{ref_col}" LIMIT :limit'
                
                params = {'limit': limit}
                if search_query:
                    params['search'] = f"%{search_query}%"
                
                result = conn.execute(text(query_str), params)
                
                return [{"value": row[0], "label": str(row[0])} for row in result]
                
        except Exception as e:
            logger.error(f"Failed to get FK values for {schema}.{table}.{column}: {str(e)}")
            raise

    def close(self):
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
