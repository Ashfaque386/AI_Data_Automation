"""
Validation Engine
Validates row data against table schema and constraints.
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
import structlog

from .datatype_enforcer import DatatypeEnforcer

logger = structlog.get_logger()


class ValidationEngine:
    """Validates row data against database schema and constraints."""
    
    def __init__(self, schema_metadata: List[Dict[str, Any]], connection_engine):
        """
        Initialize validation engine.
        
        Args:
            schema_metadata: List of column metadata from SchemaReader
            connection_engine: SQLAlchemy engine for FK validation
        """
        self.schema_metadata = {col['name']: col for col in schema_metadata}
        self.engine = connection_engine
    
    def validate_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single row of data.
        
        Args:
            row_data: Dictionary of column_name -> value
            
        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'errors': List[str],
                'column_errors': Dict[column_name, error_message]
            }
        """
        errors = []
        column_errors = {}
        
        # Validate each column
        for col_name, col_meta in self.schema_metadata.items():
            value = row_data.get(col_name)
            
            # Skip autoincrement columns if not provided
            if col_meta.get('autoincrement') and value is None:
                continue
            
            # NOT NULL validation
            if not col_meta['nullable'] and (value is None or value == ''):
                error_msg = f"{col_name}: NULL value not allowed"
                errors.append(error_msg)
                column_errors[col_name] = "Required field"
                continue
            
            # Skip further validation if value is NULL and column is nullable
            if value is None and col_meta['nullable']:
                continue
            
            # Datatype validation
            is_valid, error_msg = DatatypeEnforcer.validate_datatype(
                value, 
                col_meta['type'], 
                col_meta['nullable']
            )
            if not is_valid:
                errors.append(f"{col_name}: {error_msg}")
                column_errors[col_name] = error_msg
                continue
            
            # Length validation for string types
            if 'VARCHAR' in col_meta['type'].upper() or 'CHAR' in col_meta['type'].upper():
                is_valid, error_msg = DatatypeEnforcer.validate_length(value, col_meta['type'])
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                    column_errors[col_name] = error_msg
            
            # Precision validation for decimal types
            if 'DECIMAL' in col_meta['type'].upper() or 'NUMERIC' in col_meta['type'].upper():
                try:
                    from decimal import Decimal
                    decimal_value = Decimal(str(value))
                    is_valid, error_msg = DatatypeEnforcer.validate_precision(decimal_value, col_meta['type'])
                    if not is_valid:
                        errors.append(f"{col_name}: {error_msg}")
                        column_errors[col_name] = error_msg
                except:
                    pass
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'column_errors': column_errors
        }
    
    def validate_batch(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate multiple rows.
        
        Args:
            rows: List of row dictionaries
            
        Returns:
            Dictionary with batch validation results:
            {
                'is_valid': bool,
                'total_rows': int,
                'valid_rows': int,
                'invalid_rows': int,
                'row_results': List[Dict] (per-row validation results)
            }
        """
        row_results = []
        valid_count = 0
        
        for idx, row in enumerate(rows):
            result = self.validate_row(row)
            result['row_index'] = idx
            row_results.append(result)
            
            if result['is_valid']:
                valid_count += 1
        
        return {
            'is_valid': valid_count == len(rows),
            'total_rows': len(rows),
            'valid_rows': valid_count,
            'invalid_rows': len(rows) - valid_count,
            'row_results': row_results
        }
    
    def validate_unique_constraint(
        self, 
        schema: str, 
        table: str, 
        column: str, 
        value: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a value violates a unique constraint.
        
        Args:
            schema: Schema name
            table: Table name
            column: Column name
            value: Value to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            return (True, None)
        
        try:
            with self.engine.connect() as conn:
                query = text(f'SELECT COUNT(*) FROM "{schema}"."{table}" WHERE "{column}" = :value')
                count = conn.execute(query, {"value": value}).scalar()
                
                if count > 0:
                    return (False, f"Value '{value}' already exists (unique constraint)")
                return (True, None)
        except Exception as e:
            logger.error(f"Failed to check unique constraint: {str(e)}")
            return (False, f"Failed to validate uniqueness: {str(e)}")
    
    def validate_foreign_key(
        self, 
        ref_schema: str, 
        ref_table: str, 
        ref_column: str, 
        value: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a foreign key value exists in the referenced table.
        
        Args:
            ref_schema: Referenced schema name
            ref_table: Referenced table name
            ref_column: Referenced column name
            value: Value to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            return (True, None)
        
        try:
            with self.engine.connect() as conn:
                query = text(f'SELECT COUNT(*) FROM "{ref_schema}"."{ref_table}" WHERE "{ref_column}" = :value')
                count = conn.execute(query, {"value": value}).scalar()
                
                if count == 0:
                    return (False, f"Foreign key value '{value}' does not exist in {ref_table}.{ref_column}")
                return (True, None)
        except Exception as e:
            logger.error(f"Failed to check foreign key: {str(e)}")
            return (False, f"Failed to validate foreign key: {str(e)}")
