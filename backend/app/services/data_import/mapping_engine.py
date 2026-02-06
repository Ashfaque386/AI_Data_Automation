"""
Mapping Engine
Handles column mapping and type conversion logic
"""
from typing import Dict, List, Any, Optional
from sqlalchemy import inspect
import pandas as pd
import structlog

logger = structlog.get_logger()


class MappingEngine:
    """Handles column mapping between datasets and database tables"""
    
    # Type compatibility matrix
    TYPE_COMPATIBILITY = {
        'integer': ['integer', 'bigint', 'smallint', 'numeric', 'decimal'],
        'float': ['real', 'double precision', 'numeric', 'decimal', 'float'],
        'string': ['character varying', 'varchar', 'text', 'char', 'character'],
        'boolean': ['boolean', 'bool'],
        'datetime': ['timestamp', 'timestamp without time zone', 'timestamp with time zone', 'date', 'time'],
        'date': ['date', 'timestamp', 'timestamp without time zone'],
    }
    
    def __init__(self):
        self.logger = logger.bind(component="mapping_engine")
    
    def auto_map_columns(
        self,
        dataset_columns: List[Dict[str, Any]],
        table_columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Auto-map columns by name matching
        
        Args:
            dataset_columns: List of {name, type, nullable}
            table_columns: List of {name, type, nullable, is_primary_key}
            
        Returns:
            Mapping configuration
        """
        mappings = []
        unmapped_dataset_cols = []
        unmapped_table_cols = []
        
        # Create lookup dictionaries
        dataset_lookup = {col['name'].lower(): col for col in dataset_columns}
        table_lookup = {col['name'].lower(): col for col in table_columns}
        
        # Try to match by name
        for ds_col in dataset_columns:
            ds_name_lower = ds_col['name'].lower()
            
            if ds_name_lower in table_lookup:
                tbl_col = table_lookup[ds_name_lower]
                
                # Check type compatibility
                compatible = self._check_type_compatibility(
                    ds_col['type'],
                    tbl_col['type']
                )
                
                mappings.append({
                    'source_column': ds_col['name'],
                    'target_column': tbl_col['name'],
                    'source_type': ds_col['type'],
                    'target_type': tbl_col['type'],
                    'compatible': compatible,
                    'transformation': None,
                    'default_value': None
                })
            else:
                unmapped_dataset_cols.append(ds_col['name'])
        
        # Find unmapped table columns
        mapped_table_cols = {m['target_column'].lower() for m in mappings}
        for tbl_col in table_columns:
            if tbl_col['name'].lower() not in mapped_table_cols:
                unmapped_table_cols.append({
                    'name': tbl_col['name'],
                    'type': tbl_col['type'],
                    'nullable': tbl_col.get('nullable', True),
                    'is_primary_key': tbl_col.get('is_primary_key', False)
                })
        
        return {
            'mappings': mappings,
            'unmapped_dataset_columns': unmapped_dataset_cols,
            'unmapped_table_columns': unmapped_table_cols,
            'auto_mapped_count': len(mappings)
        }
    
    def validate_mapping(
        self,
        mappings: List[Dict[str, Any]],
        table_columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate column mappings
        
        Returns:
            Validation results with errors and warnings
        """
        errors = []
        warnings = []
        
        # Create table column lookup
        table_lookup = {col['name'].lower(): col for col in table_columns}
        mapped_targets = set()
        
        for mapping in mappings:
            target_col = mapping['target_column']
            target_col_lower = target_col.lower()
            
            # Check if target column exists
            if target_col_lower not in table_lookup:
                errors.append(f"Target column '{target_col}' does not exist in table")
                continue
            
            # Check for duplicate mappings
            if target_col_lower in mapped_targets:
                errors.append(f"Duplicate mapping to column '{target_col}'")
            mapped_targets.add(target_col_lower)
            
            # Check type compatibility
            if not mapping.get('compatible', False):
                warnings.append(
                    f"Type mismatch: {mapping['source_column']} "
                    f"({mapping['source_type']}) → {target_col} ({mapping['target_type']})"
                )
        
        # Check for unmapped required columns
        for col in table_columns:
            col_lower = col['name'].lower()
            if col_lower not in mapped_targets:
                if not col.get('nullable', True) and not col.get('has_default', False):
                    errors.append(
                        f"Required column '{col['name']}' is not mapped and has no default value"
                    )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _check_type_compatibility(self, source_type: str, target_type: str) -> bool:
        """Check if source type can be converted to target type"""
        source_type = source_type.lower()
        target_type = target_type.lower()
        
        # Exact match
        if source_type == target_type:
            return True
        
        # Check compatibility matrix
        for base_type, compatible_types in self.TYPE_COMPATIBILITY.items():
            if source_type in [base_type] + compatible_types:
                if target_type in compatible_types:
                    return True
        
        # String can convert to most types
        if source_type in ['string', 'text', 'varchar']:
            return True
        
        return False
    
    def apply_mapping(
        self,
        df: pd.DataFrame,
        mappings: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Apply column mappings to dataframe
        
        Args:
            df: Source dataframe
            mappings: List of column mappings
            
        Returns:
            Mapped dataframe
        """
        result = pd.DataFrame()
        
        for mapping in mappings:
            source_col = mapping['source_column']
            target_col = mapping['target_column']
            
            if source_col in df.columns:
                # Apply transformation if specified
                if mapping.get('transformation'):
                    # TODO: Implement transformations
                    result[target_col] = df[source_col]
                else:
                    result[target_col] = df[source_col]
            elif mapping.get('default_value') is not None:
                # Use default value
                result[target_col] = mapping['default_value']
        
        return result
