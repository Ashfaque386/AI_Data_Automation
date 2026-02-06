"""
Audit Logger
Logs table entry operations for governance and compliance.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import structlog

from app.models import User

logger = structlog.get_logger()


class TableEntryAuditLogger:
    """Logs table entry operations."""
    
    @staticmethod
    def log_insert_operation(
        db: Session,
        user: User,
        connection_id: int,
        schema: str,
        table: str,
        rows_attempted: int,
        rows_inserted: int,
        rows_failed: int,
        insert_mode: str,
        error_details: Optional[List[Dict]] = None,
        mask_values: bool = True
    ) -> int:
        """
        Log an insert operation to the audit table.
        
        Args:
            db: Database session
            user: User who performed the operation
            connection_id: Connection profile ID
            schema: Target schema
            table: Target table
            rows_attempted: Number of rows attempted
            rows_inserted: Number of rows successfully inserted
            rows_failed: Number of rows that failed
            insert_mode: Insert mode (transaction, row-by-row)
            error_details: List of error details for failed rows
            mask_values: Whether to mask sensitive values in logs
            
        Returns:
            Audit log ID
        """
        from app.models.audit import TableEntryAudit
        
        # Mask sensitive data if requested
        masked_errors = error_details
        if mask_values and error_details:
            masked_errors = []
            for error in error_details:
                masked_error = error.copy()
                if 'row_data' in masked_error:
                    masked_error['row_data'] = {
                        k: '***MASKED***' for k in masked_error['row_data'].keys()
                    }
                masked_errors.append(masked_error)
        
        audit_log = TableEntryAudit(
            user_id=user.id,
            connection_id=connection_id,
            target_schema=schema,
            target_table=table,
            rows_attempted=rows_attempted,
            rows_inserted=rows_inserted,
            rows_failed=rows_failed,
            insert_mode=insert_mode,
            error_details=masked_errors,
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        logger.info(
            "Table entry operation logged",
            user_id=user.id,
            table=f"{schema}.{table}",
            rows_inserted=rows_inserted,
            rows_failed=rows_failed
        )
        
        return audit_log.id
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        connection_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with optional filters.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            connection_id: Filter by connection ID
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log dictionaries
        """
        from app.models.audit import TableEntryAudit
        
        query = db.query(TableEntryAudit)
        
        if user_id:
            query = query.filter(TableEntryAudit.user_id == user_id)
        if connection_id:
            query = query.filter(TableEntryAudit.connection_id == connection_id)
        
        logs = query.order_by(TableEntryAudit.created_at.desc()).limit(limit).all()
        
        return [
            {
                'id': log.id,
                'user_id': log.user_id,
                'connection_id': log.connection_id,
                'target_schema': log.target_schema,
                'target_table': log.target_table,
                'rows_attempted': log.rows_attempted,
                'rows_inserted': log.rows_inserted,
                'rows_failed': log.rows_failed,
                'insert_mode': log.insert_mode,
                'error_details': log.error_details,
                'created_at': log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
