"""
Audit Logging Service
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog
import hashlib

from app.models import AuditLog, QueryHistory, User

logger = structlog.get_logger()


class AuditLogger:
    """Centralized audit logging service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        user: Optional[User] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        rows_affected: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        connection_id: Optional[int] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        audit = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            details=details,
            query_text=query_text,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            connection_id=connection_id
        )
        
        self.db.add(audit)
        self.db.commit()
        
        # Also log to structured logger
        log_method = logger.info if status == "success" else logger.warning
        log_method(
            "audit_event",
            action=action,
            user_email=user.email if user else None,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            connection_id=connection_id
        )
        
        return audit
    
    def log_login(self, user: User, ip_address: str = None, success: bool = True):
        """Log login attempt."""
        return self.log(
            action="login",
            user=user if success else None,
            resource_type="auth",
            status="success" if success else "failure",
            ip_address=ip_address,
            details={"email": user.email if user else None}
        )
    
    def log_upload(self, user: User, dataset_name: str, dataset_id: int, 
                   file_type: str, row_count: int):
        """Log file upload."""
        return self.log(
            action="upload",
            user=user,
            resource_type="dataset",
            resource_id=str(dataset_id),
            resource_name=dataset_name,
            details={"file_type": file_type, "row_count": row_count}
        )
    
    def log_query(self, user: User, query: str, duration_ms: int, 
                  rows_affected: int = 0, success: bool = True, 
                  error: str = None, connection_id: int = None):
        """Log SQL query execution."""
        return self.log(
            action="query_execute",
            user=user,
            resource_type="sql",
            query_text=query[:10000],  # Truncate very long queries
            status="success" if success else "failure",
            error_message=error,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            connection_id=connection_id
        )
    
    def log_export(self, user: User, dataset_name: str, dataset_id: int,
                   export_format: str, row_count: int):
        """Log data export."""
        return self.log(
            action="export",
            user=user,
            resource_type="dataset",
            resource_id=str(dataset_id),
            resource_name=dataset_name,
            details={"format": export_format, "row_count": row_count}
        )
    
    def log_edit(self, user: User, dataset_name: str, dataset_id: int,
                 changes: Dict[str, Any]):
        """Log data edit."""
        return self.log(
            action="edit",
            user=user,
            resource_type="dataset",
            resource_id=str(dataset_id),
            resource_name=dataset_name,
            details=changes
        )


class QueryHistoryManager:
    """Manage SQL query history."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query deduplication."""
        normalized = " ".join(query.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def record_query(self, user_id: int, query: str, duration_ms: int, connection_id: int = None) -> QueryHistory:
        """Record a query execution."""
        query_hash = self._hash_query(query)
        
        # Check for existing query
        existing = self.db.query(QueryHistory).filter(
            QueryHistory.user_id == user_id,
            QueryHistory.query_hash == query_hash
        ).first()
        
        if existing:
            # Update existing
            existing.execution_count += 1
            existing.last_executed_at = datetime.utcnow()
            if existing.avg_duration_ms:
                existing.avg_duration_ms = (existing.avg_duration_ms + duration_ms) // 2
            else:
                existing.avg_duration_ms = duration_ms
            self.db.commit()
            return existing
        else:
            # Create new
            history = QueryHistory(
                user_id=user_id,
                query_text=query,
                query_hash=query_hash,
                last_executed_at=datetime.utcnow(),
                avg_duration_ms=duration_ms
            )
            self.db.add(history)
            self.db.commit()
            return history
    
    def save_query(self, user_id: int, query_id: int, name: str) -> Optional[QueryHistory]:
        """Save a query with a name."""
        history = self.db.query(QueryHistory).filter(
            QueryHistory.id == query_id,
            QueryHistory.user_id == user_id
        ).first()
        
        if history:
            history.name = name
            history.is_saved = True
            self.db.commit()
        
        return history
    
    def toggle_favorite(self, user_id: int, query_id: int) -> Optional[QueryHistory]:
        """Toggle favorite status of a query."""
        history = self.db.query(QueryHistory).filter(
            QueryHistory.id == query_id,
            QueryHistory.user_id == user_id
        ).first()
        
        if history:
            history.is_favorite = not history.is_favorite
            self.db.commit()
        
        return history
    
    def get_user_history(self, user_id: int, limit: int = 100, 
                         saved_only: bool = False) -> list:
        """Get query history for a user."""
        query = self.db.query(QueryHistory).filter(
            QueryHistory.user_id == user_id
        )
        
        if saved_only:
            query = query.filter(QueryHistory.is_saved == True)
        
        return query.order_by(QueryHistory.last_executed_at.desc()).limit(limit).all()
