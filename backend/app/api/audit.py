"""
Audit Logs API
Endpoints for querying and managing audit logs
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog, AuditActionType
from app.services.audit_service import audit_service
from app.api.auth import get_current_user


router = APIRouter(prefix="/audit", tags=["audit"])


# Pydantic models
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int]
    user_email: Optional[str]
    connection_id: Optional[int]
    connection_name: Optional[str]
    action: str
    action_type: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    resource_name: Optional[str]
    details: Optional[dict]
    query_text: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    error_message: Optional[str]
    duration_ms: Optional[int]
    rows_affected: Optional[int]
    
    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    total_actions: int
    successful_actions: int
    failed_actions: int
    success_rate: float
    action_breakdown: dict


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    connection_id: Optional[int] = Query(None, description="Filter by connection ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    success_only: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit logs with optional filters
    """
    # Convert action_type string to enum if provided
    action_type_enum = None
    if action_type:
        try:
            action_type_enum = AuditActionType(action_type)
        except ValueError:
            pass
    
    logs = audit_service.get_audit_logs(
        db=db,
        user_id=user_id,
        connection_id=connection_id,
        action_type=action_type_enum,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        success_only=success_only,
        limit=limit,
        offset=offset
    )
    
    return logs


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific audit log by ID
    """
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return log


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    connection_id: Optional[int] = Query(None, description="Filter by connection ID"),
    days: int = Query(7, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audit statistics
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    stats = audit_service.get_audit_stats(
        db=db,
        user_id=user_id,
        connection_id=connection_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return stats


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    user_id: Optional[int] = Query(None),
    connection_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export audit logs in CSV or JSON format
    """
    from fastapi.responses import StreamingResponse
    import csv
    import json
    from io import StringIO
    
    logs = audit_service.get_audit_logs(
        db=db,
        user_id=user_id,
        connection_id=connection_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000  # Max export limit
    )
    
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "ID", "Timestamp", "User Email", "Connection Name", "Action",
            "Resource Type", "Resource Name", "Status", "Duration (ms)", "IP Address"
        ])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at,
                log.user_email,
                log.connection_name,
                log.action,
                log.resource_type,
                log.resource_name,
                log.status,
                log.duration_ms,
                log.ip_address
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    
    else:  # JSON
        data = [
            {
                "id": log.id,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "user_email": log.user_email,
                "connection_name": log.connection_name,
                "action": log.action,
                "action_type": log.action_type.value if log.action_type else None,
                "resource_type": log.resource_type,
                "resource_name": log.resource_name,
                "status": log.status,
                "duration_ms": log.duration_ms,
                "ip_address": log.ip_address,
                "details": log.details
            }
            for log in logs
        ]
        
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )
