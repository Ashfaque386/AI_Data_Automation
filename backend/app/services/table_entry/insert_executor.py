"""
Insert Executor
Safely executes INSERT operations with transaction management.
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import structlog

from .datatype_enforcer import DatatypeEnforcer

logger = structlog.get_logger()


class InsertExecutor:
    """Executes INSERT operations with safety controls."""
    
    def __init__(self, engine: Engine):
        """Initialize with a database engine."""
        self.engine = engine
    
    def insert_rows(
        self,
        schema: str,
        table: str,
        rows: List[Dict[str, Any]],
        schema_metadata: List[Dict[str, Any]],
        mode: str = "transaction"
    ) -> Dict[str, Any]:
        """
        Insert rows into a database table.
        
        Args:
            schema: Schema name
            table: Table name
            rows: List of row dictionaries (column_name -> value)
            schema_metadata: Column metadata for type coercion
            mode: Insert mode - "transaction" (all-or-nothing) or "row-by-row"
            
        Returns:
            Dictionary with execution results:
            {
                'success': bool,
                'rows_inserted': int,
                'rows_failed': int,
                'failed_rows': List[Dict],
                'error_message': Optional[str]
            }
        """
        if mode == "transaction":
            return self._insert_transaction(schema, table, rows, schema_metadata)
        elif mode == "row-by-row":
            return self._insert_row_by_row(schema, table, rows, schema_metadata)
        else:
            raise ValueError(f"Invalid insert mode: {mode}")
    
    def _insert_transaction(
        self,
        schema: str,
        table: str,
        rows: List[Dict[str, Any]],
        schema_metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert all rows in a single transaction (all-or-nothing).
        """
        try:
            with self.engine.begin() as conn:
                for row in rows:
                    self._execute_insert(conn, schema, table, row, schema_metadata)
                
                # If we get here, all inserts succeeded
                logger.info(f"Successfully inserted {len(rows)} rows into {schema}.{table}")
                return {
                    'success': True,
                    'rows_inserted': len(rows),
                    'rows_failed': 0,
                    'failed_rows': [],
                    'error_message': None
                }
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return {
                'success': False,
                'rows_inserted': 0,
                'rows_failed': len(rows),
                'failed_rows': rows,
                'error_message': str(e)
            }
    
    def _insert_row_by_row(
        self,
        schema: str,
        table: str,
        rows: List[Dict[str, Any]],
        schema_metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Insert rows one by one, continuing on failure.
        """
        inserted_count = 0
        failed_rows = []
        
        for idx, row in enumerate(rows):
            try:
                with self.engine.begin() as conn:
                    self._execute_insert(conn, schema, table, row, schema_metadata)
                    inserted_count += 1
                    logger.info(f"Inserted row {idx + 1}/{len(rows)}")
            except Exception as e:
                logger.error(f"Failed to insert row {idx + 1}: {str(e)}")
                failed_rows.append({
                    'row_index': idx,
                    'row_data': row,
                    'error': str(e)
                })
        
        return {
            'success': inserted_count == len(rows),
            'rows_inserted': inserted_count,
            'rows_failed': len(failed_rows),
            'failed_rows': failed_rows,
            'error_message': None if inserted_count == len(rows) else f"{len(failed_rows)} rows failed"
        }
    
    def _execute_insert(
        self,
        conn,
        schema: str,
        table: str,
        row: Dict[str, Any],
        schema_metadata: List[Dict[str, Any]]
    ):
        """
        Execute a single INSERT statement using prepared statement.
        """
        # Build column metadata map
        col_meta_map = {col['name']: col for col in schema_metadata}
        
        # Filter out autoincrement columns if they're NULL
        filtered_row = {}
        for col_name, value in row.items():
            col_meta = col_meta_map.get(col_name)
            if col_meta and col_meta.get('autoincrement') and value is None:
                continue
            filtered_row[col_name] = value
        
        # Coerce values to correct types
        coerced_row = {}
        for col_name, value in filtered_row.items():
            col_meta = col_meta_map.get(col_name)
            if col_meta:
                coerced_value = DatatypeEnforcer.coerce_value(
                    value,
                    col_meta['type'],
                    col_meta['nullable']
                )
                coerced_row[col_name] = coerced_value
            else:
                coerced_row[col_name] = value
        
        # Build INSERT statement
        columns = list(coerced_row.keys())
        placeholders = [f":{col}" for col in columns]
        
        insert_sql = f'''
            INSERT INTO "{schema}"."{table}" ({", ".join(f'"{col}"' for col in columns)})
            VALUES ({", ".join(placeholders)})
        '''
        
        # Execute with prepared statement
        conn.execute(text(insert_sql), coerced_row)
