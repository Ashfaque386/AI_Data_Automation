"""
Datatype Enforcer
Handles type coercion and validation for database column types.
"""
from typing import Any, Optional
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import structlog

logger = structlog.get_logger()


class DatatypeEnforcer:
    """Enforces and validates database datatypes."""
    
    @staticmethod
    def coerce_value(value: Any, column_type: str, nullable: bool = True) -> Any:
        """
        Convert input value to the appropriate Python type for the column.
        
        Args:
            value: Input value (usually string from UI)
            column_type: Database column type (e.g., 'INTEGER', 'VARCHAR(255)')
            nullable: Whether the column allows NULL
            
        Returns:
            Coerced value in the correct Python type
            
        Raises:
            ValueError: If value cannot be coerced to the target type
        """
        # Handle NULL/None
        if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
            if nullable:
                return None
            else:
                raise ValueError("NULL value not allowed for non-nullable column")
        
        # Normalize column type (uppercase, extract base type)
        col_type_upper = column_type.upper()
        base_type = col_type_upper.split('(')[0].strip()
        
        try:
            # Integer types
            if base_type in ('INTEGER', 'INT', 'SMALLINT', 'BIGINT', 'SERIAL', 'BIGSERIAL'):
                return int(value)
            
            # Decimal/Numeric types
            elif base_type in ('DECIMAL', 'NUMERIC', 'REAL', 'DOUBLE', 'FLOAT'):
                return Decimal(str(value))
            
            # String types
            elif base_type in ('VARCHAR', 'CHAR', 'TEXT', 'STRING'):
                return str(value)
            
            # Boolean types
            elif base_type in ('BOOLEAN', 'BOOL'):
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    if value.lower() in ('true', '1', 'yes', 't', 'y'):
                        return True
                    elif value.lower() in ('false', '0', 'no', 'f', 'n'):
                        return False
                return bool(value)
            
            # Date types
            elif base_type == 'DATE':
                if isinstance(value, date):
                    return value
                if isinstance(value, datetime):
                    return value.date()
                # Try parsing string
                return datetime.fromisoformat(str(value)).date()
            
            # Timestamp/DateTime types
            elif base_type in ('TIMESTAMP', 'DATETIME'):
                if isinstance(value, datetime):
                    return value
                # Try parsing string
                return datetime.fromisoformat(str(value))
            
            # JSON types
            elif base_type in ('JSON', 'JSONB'):
                if isinstance(value, (dict, list)):
                    return value
                # Try parsing string as JSON
                import json
                return json.loads(str(value))
            
            # Default: return as string
            else:
                logger.warning(f"Unknown column type {column_type}, treating as string")
                return str(value)
                
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Cannot convert '{value}' to {column_type}: {str(e)}")
    
    @staticmethod
    def validate_datatype(value: Any, column_type: str, nullable: bool = True) -> tuple[bool, Optional[str]]:
        """
        Validate that a value matches the expected datatype.
        
        Args:
            value: Value to validate
            column_type: Database column type
            nullable: Whether the column allows NULL
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to coerce - if it succeeds, it's valid
            DatatypeEnforcer.coerce_value(value, column_type, nullable)
            return (True, None)
        except ValueError as e:
            return (False, str(e))
    
    @staticmethod
    def validate_length(value: str, column_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate string length against column type constraints.
        
        Args:
            value: String value to validate
            column_type: Column type (e.g., 'VARCHAR(255)')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            return (True, None)
        
        # Extract length constraint
        if '(' in column_type and ')' in column_type:
            try:
                length_str = column_type.split('(')[1].split(')')[0]
                max_length = int(length_str.split(',')[0])  # Handle DECIMAL(10,2) format
                
                if len(str(value)) > max_length:
                    return (False, f"Value exceeds maximum length of {max_length}")
            except (ValueError, IndexError):
                pass
        
        return (True, None)
    
    @staticmethod
    def validate_precision(value: Decimal, column_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate decimal precision and scale.
        
        Args:
            value: Decimal value to validate
            column_type: Column type (e.g., 'DECIMAL(10,2)')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            return (True, None)
        
        # Extract precision and scale
        if '(' in column_type and ')' in column_type:
            try:
                params = column_type.split('(')[1].split(')')[0].split(',')
                if len(params) == 2:
                    precision = int(params[0])
                    scale = int(params[1])
                    
                    # Convert to string to count digits
                    value_str = str(value).replace('.', '').replace('-', '')
                    total_digits = len(value_str)
                    
                    if total_digits > precision:
                        return (False, f"Value exceeds precision of {precision}")
                    
                    # Check scale (decimal places)
                    if '.' in str(value):
                        decimal_places = len(str(value).split('.')[1])
                        if decimal_places > scale:
                            return (False, f"Value exceeds scale of {scale}")
            except (ValueError, IndexError):
                pass
        
        return (True, None)
