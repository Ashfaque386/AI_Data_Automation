"""
Audit Service
Centralized service for logging all system actions
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from datetime import datetime

from app.models.audit import AuditLog, AuditActionType
from app.models.user import User


class AuditService:
    """Service for creating and querying audit logs"""
    
    @staticmethod
    async def log_action(
        db: Session,
        user_id: Optional[int],
        action_type: AuditActionType,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        connection_id: Optional[int] = None,
        connection_name: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        rows_affected: Optional[int] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Create an audit log entry
        
        Args:
            db: Database session
            user_id: ID of the user performing the action
            action_type: Type of action (from AuditActionType enum)
            resource_type: Type of resource (connection, query, schema, table, etc.)
            resource_id: ID of the resource
            resource_name: Name of the resource
            action_details: Additional details about the action (JSON)
            query_text: SQL query text (for query operations)
            connection_id: ID of the connection (if applicable)
            connection_name: Name of the connection (if applicable)
            success: Whether the action was successful
            error_message: Error message (if failed)
            duration_ms: Execution duration in milliseconds
            rows_affected: Number of rows affected (for data operations)
            request: FastAPI request object (for IP and user agent)
        
        Returns:
            Created AuditLog instance
        """
        # Get user email if user_id provided
        user_email = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user_email = user.email
        
        # Extract IP and user agent from request
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            connection_id=connection_id,
            connection_name=connection_name,
            action=action_type.value,  # For backward compatibility
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=action_details,
            query_text=query_text,
            status='success' if success else 'failure',
            error_message=error_message,
            duration_ms=duration_ms,
            rows_affected=rows_affected
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        connection_id: Optional[int] = None,
        action_type: Optional[AuditActionType] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        success_only: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ):
        """
        Query audit logs with filters
        
        Args:
            db: Database session
            user_id: Filter by user ID
            connection_id: Filter by connection ID
            action_type: Filter by action type
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            success_only: Filter by success status
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of AuditLog instances
        """
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if connection_id:
            query = query.filter(AuditLog.connection_id == connection_id)
        
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        if success_only is not None:
            status = 'success' if success_only else 'failure'
            query = query.filter(AuditLog.status == status)
        
        query = query.order_by(AuditLog.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    @staticmethod
    def get_audit_stats(
        db: Session,
        user_id: Optional[int] = None,
        connection_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics
        
        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import func, case
        
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if connection_id:
            query = query.filter(AuditLog.connection_id == connection_id)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        # Get counts
        total_actions = query.count()
        successful_actions = query.filter(AuditLog.status == 'success').count()
        failed_actions = query.filter(AuditLog.status == 'failure').count()
        
        # Get action type breakdown
        action_breakdown = db.query(
            AuditLog.action_type,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date if start_date else True,
            AuditLog.created_at <= end_date if end_date else True
        ).group_by(AuditLog.action_type).all()
        
        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
            'action_breakdown': {str(action): count for action, count in action_breakdown}
        }


# Global audit service instance
audit_service = AuditService()
