"""
Validation Engine
Validates data before import
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import structlog

logger = structlog.get_logger()


class ValidationEngine:
    """Validates data before database import"""
    
    def __init__(self):
        self.logger = logger.bind(component="validation_engine")
    
    def validate_data(
        self,
        df: pd.DataFrame,
        table_schema: List[Dict[str, Any]],
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        Validate dataframe against table schema
        
        Args:
            df: Dataframe to validate
            table_schema: Target table schema
            sample_size: Number of rows to validate in detail
            
        Returns:
            Validation results
        """
        errors = []
        warnings = []
        row_errors = []
        
        # Create schema lookup
        schema_lookup = {col['name'].lower(): col for col in table_schema}
        
        # Validate each column
        for col_name in df.columns:
            col_lower = col_name.lower()
            
            if col_lower not in schema_lookup:
                warnings.append(f"Column '{col_name}' not in target table schema")
                continue
            
            col_schema = schema_lookup[col_lower]
            col_data = df[col_name]
            
            # Check for null values in non-nullable columns
            if not col_schema.get('nullable', True):
                null_count = col_data.isnull().sum()
                if null_count > 0:
                    errors.append(
                        f"Column '{col_name}' has {null_count} null values but is NOT NULL"
                    )
            
            # Check data type compatibility
            target_type = col_schema['type'].lower()
            validation_result = self._validate_column_type(
                col_data,
                target_type,
                col_name
            )
            
            if validation_result['errors']:
                errors.extend(validation_result['errors'])
            if validation_result['warnings']:
                warnings.extend(validation_result['warnings'])
            
            # Check string length constraints
            if 'max_length' in col_schema:
                max_len = col_schema['max_length']
                long_values = col_data[col_data.astype(str).str.len() > max_len]
                if len(long_values) > 0:
                    errors.append(
                        f"Column '{col_name}' has {len(long_values)} values "
                        f"exceeding max length {max_len}"
                    )
        
        # Sample row-level validation
        sample_df = df.head(sample_size)
        for idx, row in sample_df.iterrows():
            row_validation = self._validate_row(row, schema_lookup)
            if row_validation['errors']:
                row_errors.append({
                    'row_index': idx,
                    'errors': row_validation['errors']
                })
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'row_errors': row_errors,
            'total_rows': len(df),
            'validated_rows': len(sample_df)
        }
    
    def _validate_column_type(
        self,
        col_data: pd.Series,
        target_type: str,
        col_name: str
    ) -> Dict[str, Any]:
        """Validate column data type compatibility"""
        errors = []
        warnings = []
        
        # Skip null values
        non_null_data = col_data.dropna()
        if len(non_null_data) == 0:
            return {'errors': errors, 'warnings': warnings}
        
        # Integer types
        if target_type in ['integer', 'bigint', 'smallint']:
            try:
                pd.to_numeric(non_null_data, errors='raise')
            except (ValueError, TypeError):
                invalid_count = len(non_null_data) - pd.to_numeric(non_null_data, errors='coerce').notna().sum()
                if invalid_count > 0:
                    errors.append(
                        f"Column '{col_name}' has {invalid_count} non-integer values"
                    )
        
        # Float types
        elif target_type in ['real', 'double precision', 'numeric', 'decimal', 'float']:
            try:
                pd.to_numeric(non_null_data, errors='raise')
            except (ValueError, TypeError):
                invalid_count = len(non_null_data) - pd.to_numeric(non_null_data, errors='coerce').notna().sum()
                if invalid_count > 0:
                    errors.append(
                        f"Column '{col_name}' has {invalid_count} non-numeric values"
                    )
        
        # Boolean types
        elif target_type in ['boolean', 'bool']:
            valid_bool_values = {True, False, 'true', 'false', 't', 'f', 1, 0, '1', '0', 'yes', 'no'}
            invalid_values = non_null_data[~non_null_data.isin(valid_bool_values)]
            if len(invalid_values) > 0:
                errors.append(
                    f"Column '{col_name}' has {len(invalid_values)} invalid boolean values"
                )
        
        # Date/Time types
        elif target_type in ['timestamp', 'date', 'time']:
            try:
                pd.to_datetime(non_null_data, errors='raise')
            except (ValueError, TypeError):
                invalid_count = len(non_null_data) - pd.to_datetime(non_null_data, errors='coerce').notna().sum()
                if invalid_count > 0:
                    errors.append(
                        f"Column '{col_name}' has {invalid_count} invalid date/time values"
                    )
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_row(
        self,
        row: pd.Series,
        schema_lookup: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a single row"""
        errors = []
        
        for col_name, value in row.items():
            col_lower = col_name.lower()
            if col_lower not in schema_lookup:
                continue
            
            col_schema = schema_lookup[col_lower]
            
            # Check null constraint
            if pd.isna(value) and not col_schema.get('nullable', True):
                errors.append(f"NULL value in non-nullable column '{col_name}'")
        
        return {'errors': errors}
    
    def check_primary_key_duplicates(
        self,
        df: pd.DataFrame,
        primary_key_columns: List[str]
    ) -> Dict[str, Any]:
        """Check for duplicate primary key values"""
        if not primary_key_columns:
            return {'has_duplicates': False, 'duplicate_count': 0}
        
        # Filter to only PK columns that exist in df
        existing_pk_cols = [col for col in primary_key_columns if col in df.columns]
        
        if not existing_pk_cols:
            return {'has_duplicates': False, 'duplicate_count': 0}
        
        duplicates = df[df.duplicated(subset=existing_pk_cols, keep=False)]
        
        return {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'duplicate_rows': duplicates.index.tolist()[:100]  # Limit to first 100
        }
