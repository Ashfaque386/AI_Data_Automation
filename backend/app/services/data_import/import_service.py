"""
Import Service
Main orchestration for data import operations
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
import structlog

from app.models import ImportJob, ImportAuditLog, Dataset, ConnectionProfile
from app.services.data_import.mapping_engine import MappingEngine
from app.services.data_import.validation_engine import ValidationEngine
from app.services.data_import.execution_engine import ExecutionEngine
from app.core.crypto import decrypt_value

logger = structlog.get_logger()


class ImportService:
    """Main service for data import operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.mapping_engine = MappingEngine()
        self.validation_engine = ValidationEngine()
        self.logger = logger.bind(component="import_service")
    
    def get_dataset_preview(
        self,
        dataset_id: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get dataset preview for import"""
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Load dataset data
        # TODO: Implement based on your dataset storage
        # For now, return mock data
        return {
            'dataset_id': dataset.id,
            'name': dataset.name,
            'row_count': dataset.row_count,
            'columns': [
                {'name': col.name, 'type': col.data_type}
                for col in dataset.columns
            ]
        }
    
    def get_table_info(
        self,
        connection_id: int,
        table_name: str,
        schema: str = "public"
    ) -> Dict[str, Any]:
        """Get target table information"""
        connection = self.db.query(ConnectionProfile).filter(
            ConnectionProfile.id == connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Build connection string
        password = decrypt_value(connection.encrypted_password)
        conn_string = (
            f"postgresql://{connection.username}:{password}"
            f"@{connection.host}:{connection.port}/{connection.database}"
        )
        
        exec_engine = ExecutionEngine(conn_string)
        try:
            schema_info = exec_engine.get_table_schema(table_name, schema)
            return {
                'table_name': table_name,
                'schema': schema,
                'columns': schema_info
            }
        finally:
            exec_engine.disconnect()
    
    def create_auto_mapping(
        self,
        dataset_id: int,
        connection_id: int,
        table_name: str,
        schema: str = "public"
    ) -> Dict[str, Any]:
        """Create automatic column mapping"""
        # Get dataset columns
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        dataset_columns = [
            {'name': col.name, 'type': col.data_type, 'nullable': True}
            for col in dataset.columns
        ]
        
        # Get table columns
        table_info = self.get_table_info(connection_id, table_name, schema)
        table_columns = table_info['columns']
        
        # Auto-map
        mapping_result = self.mapping_engine.auto_map_columns(
            dataset_columns,
            table_columns
        )
        
        return mapping_result
    
    def validate_import(
        self,
        dataset_id: int,
        connection_id: int,
        table_name: str,
        schema: str,
        mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate import configuration"""
        # Get table schema
        table_info = self.get_table_info(connection_id, table_name, schema)
        
        # Validate mapping
        mapping_validation = self.mapping_engine.validate_mapping(
            mappings,
            table_info['columns']
        )
        
        # TODO: Load and validate actual data
        # For now, return mapping validation
        return {
            'mapping_valid': mapping_validation['valid'],
            'mapping_errors': mapping_validation['errors'],
            'mapping_warnings': mapping_validation['warnings']
        }
    
    def execute_import(
        self,
        job_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Execute import job"""
        job = self.db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            raise ValueError(f"Import job {job_id} not found")
        
        try:
            # Update job status
            job.status = "running"
            from datetime import datetime
            job.started_at = datetime.utcnow()
            self.db.commit()
            
            # Log start
            self._log_audit(job_id, user_id, "import_started", {
                'table': job.target_table,
                'mode': job.import_mode
            })
            
            # Get connection
            connection = self.db.query(ConnectionProfile).filter(
                ConnectionProfile.id == job.target_connection_id
            ).first()
            
            password = decrypt_value(connection.encrypted_password)
            conn_string = (
                f"postgresql://{connection.username}:{password}"
                f"@{connection.host}:{connection.port}/{connection.database}"
            )
            
            # TODO: Load dataset data into dataframe
            # For now, create empty dataframe
            df = pd.DataFrame()
            
            # Apply mapping
            mapped_df = self.mapping_engine.apply_mapping(
                df,
                job.mapping_config['mappings']
            )
            
            # Execute import
            exec_engine = ExecutionEngine(conn_string)
            try:
                result = exec_engine.execute_import(
                    mapped_df,
                    job.target_table,
                    job.target_schema,
                    job.import_mode,
                    job.import_config.get('batch_size', 1000)
                )
                
                # Update job with results
                job.status = "completed" if result['success'] else "failed"
                job.inserted_rows = result['inserted_rows']
                job.updated_rows = result['updated_rows']
                job.error_rows = result['error_rows']
                job.error_details = result.get('errors', [])
                job.completed_at = datetime.utcnow()
                self.db.commit()
                
                # Log completion
                self._log_audit(job_id, user_id, "import_completed", result)
                
                return result
            
            finally:
                exec_engine.disconnect()
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()
            
            self._log_audit(job_id, user_id, "import_failed", {'error': str(e)})
            raise
    
    def _log_audit(
        self,
        job_id: int,
        user_id: int,
        action: str,
        details: Dict[str, Any]
    ):
        """Log audit entry"""
        audit_log = ImportAuditLog(
            import_job_id=job_id,
            user_id=user_id,
            action=action,
            details=details
        )
        self.db.add(audit_log)
        self.db.commit()
