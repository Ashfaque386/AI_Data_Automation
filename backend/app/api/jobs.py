"""
Jobs API
Complete REST API for job management, execution, and monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import structlog
import asyncio
import json
import os

from app.database import get_app_db, get_app_db_context
from app.models import User, ScheduledJob, JobExecution, JobType, JobStatus, ConnectionProfile
from app.core.rbac import get_current_active_user, require_permission
from app.services.jobs.job_manager import JobManager
from app.services.jobs.job_scheduler import JobScheduler
from app.services.jobs.procedure_executor import ProcedureExecutor
from app.core.crypto import decrypt_value

router = APIRouter()
logger = structlog.get_logger()


# Request/Response Models

class JobParameterSchema(BaseModel):
    name: str
    value: str
    type: str
    mode: str = 'IN'


class CreateJobRequest(BaseModel):
    name: str
    description: Optional[str] = None
    job_type: str
    connection_id: int
    target_schema: Optional[str] = 'public'
    cron_expression: Optional[str] = None
    timezone: str = 'UTC'
    is_active: bool = True
    config: dict
    pre_execution_sql: Optional[str] = None
    post_execution_sql: Optional[str] = None
    retry_policy: Optional[dict] = None
    max_runtime_seconds: int = 3600
    failure_threshold: int = 5
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_emails: Optional[List[str]] = None
    notification_webhook: Optional[str] = None


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None
    pre_execution_sql: Optional[str] = None
    post_execution_sql: Optional[str] = None
    retry_policy: Optional[dict] = None
    max_runtime_seconds: Optional[int] = None
    failure_threshold: Optional[int] = None
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_emails: Optional[List[str]] = None


class QuickBackupRequest(BaseModel):
    connection_id: int
    database_name: str
    backup_type: str = 'full'
    compression_enabled: bool = True
    retention_days: int = 30
    storage_path: Optional[str] = '/app/backups'
    format: Optional[str] = 'custom'


# Job CRUD Endpoints

@router.post("/", status_code=status.HTTP_201_CREATED)
@require_permission("jobs:create")
async def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new scheduled job"""
    logger.info("create_job_request", job_type=request.job_type, user_id=current_user.id)
    
    try:
        job_manager = JobManager(db)
        job = job_manager.create_job(request.dict(), current_user.id)
        
        return {
            "id": job.id,
            "name": job.name,
            "job_type": job.job_type,
            "is_active": job.is_active,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "created_at": job.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("create_job_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
@require_permission("jobs:view")
async def list_jobs(
    job_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List scheduled jobs with filters"""
    query = db.query(ScheduledJob)
    
    # Apply filters
    if job_type:
        query = query.filter(ScheduledJob.job_type == job_type)
    if is_active is not None:
        query = query.filter(ScheduledJob.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    jobs = query.order_by(ScheduledJob.created_at.desc()).offset(offset).limit(limit).all()
    
    response_data = {
        "total": total,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "description": job.description,
                "job_type": job.job_type,
                "is_active": job.is_active,
                "cron_expression": job.cron_expression,
                "timezone": job.timezone,
                "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
                "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                "run_count": job.run_count,
                "success_count": job.success_count,
                "failure_count": job.failure_count,
                "consecutive_failures": job.consecutive_failures,
                "created_at": job.created_at.isoformat(),
                # Add last successful execution for direct download access
                "last_execution": (
                    {
                        "id": job.executions[0].id,
                        "status": job.executions[0].status,
                        "result": job.executions[0].result
                    }
                    if job.executions and len(job.executions) > 0 and job.executions[0].status == JobStatus.COMPLETED.value
                    else None
                )
            }
            for job in jobs
        ]
    }
    logger.info("list_jobs_response", jobs=json.dumps(response_data['jobs'], default=str))
    return response_data


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get job details"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "name": job.name,
        "description": job.description,
        "job_type": job.job_type,
        "connection_id": job.connection_id,
        "target_schema": job.target_schema,
        "cron_expression": job.cron_expression,
        "timezone": job.timezone,
        "is_active": job.is_active,
        "config": job.config,
        "pre_execution_sql": job.pre_execution_sql,
        "post_execution_sql": job.post_execution_sql,
        "retry_policy": job.retry_policy,
        "max_runtime_seconds": job.max_runtime_seconds,
        "failure_threshold": job.failure_threshold,
        "notify_on_success": job.notify_on_success,
        "notify_on_failure": job.notify_on_failure,
        "notification_emails": job.notification_emails,
        "notification_webhook": job.notification_webhook,
        "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
        "run_count": job.run_count,
        "success_count": job.success_count,
        "failure_count": job.failure_count,
        "consecutive_failures": job.consecutive_failures,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None
    }


@router.put("/{job_id}")
@require_permission("jobs:manage")
async def update_job(
    job_id: int,
    request: UpdateJobRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update job configuration"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    
    # Validate cron expression if being updated
    if 'cron_expression' in update_data and update_data['cron_expression']:
        is_valid, error = JobScheduler.validate_cron_expression(update_data['cron_expression'])
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid cron expression: {error}")
    
    for field, value in update_data.items():
        setattr(job, field, value)
    
    db.commit()
    
    # Recalculate next run if cron expression changed
    if 'cron_expression' in update_data or 'timezone' in update_data:
        if job.cron_expression:
            JobScheduler.update_next_run(job, db)
    
    return {"success": True, "message": "Job updated successfully"}


@router.delete("/{job_id}")
@require_permission("jobs:manage")
async def delete_job(
    job_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a job"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    
    logger.info("job_deleted", job_id=job_id, user_id=current_user.id)
    
    return {"success": True, "message": "Job deleted successfully"}


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth import verify_token, get_user_by_id

# Optional security for hybrid auth
security_optional = HTTPBearer(auto_error=False)

async def get_current_user_hybrid(
    token: Optional[str] = Query(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_app_db)
) -> User:
    """Authenticate via Header OR Query Parameter (for downloads)"""
    # Check header first
    if auth:
        payload = verify_token(auth.credentials)
        if payload:
            user = get_user_by_id(db, payload.sub)
            if user and user.is_active:
                return user
    
    # Check query param
    if token:
        payload = verify_token(token)
        if payload:
            user = get_user_by_id(db, payload.sub)
            if user and user.is_active:
                return user
                
    raise HTTPException(status_code=401, detail="Not authenticated")

@router.get("/{job_id}/executions/{execution_id}/download")
@require_permission("jobs:view")
async def download_backup(
    job_id: int,
    execution_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_user_hybrid)
):
    """Download backup file from execution result"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if execution.job_id != job_id:
        raise HTTPException(status_code=400, detail="Execution does not belong to this job")
        
    if job.job_type.lower() != JobType.DATABASE_BACKUP.value.lower(): # JobType and JobStatus need to be imported
        raise HTTPException(status_code=400, detail="Not a backup job")
        
    if execution.status.lower() != JobStatus.COMPLETED.value.lower():
        raise HTTPException(status_code=400, detail="Backup execution not completed successfully")
        
    # Extract file path from result
    result_data = execution.result
    if not result_data or 'backup_path' not in result_data:
        raise HTTPException(status_code=404, detail="Backup file information not found in execution result")
        
    file_path = result_data['backup_path']
    
    logger.info("download_backup_request", job_id=job_id, execution_id=execution_id, file_path=file_path)
    
    if not os.path.exists(file_path):
        # List directory to help debug
        dir_path = os.path.dirname(file_path)
        if os.path.exists(dir_path):
            logger.info("directory_contents", dir=dir_path, files=os.listdir(dir_path))
        else:
            logger.error("directory_not_found", dir=dir_path)
            
        raise HTTPException(status_code=404, detail=f"Backup file not found on server: {file_path}")
        
    # Check file size
    file_size = os.path.getsize(file_path)
    logger.info("serving_backup_file", file_path=file_path, size=file_size)
    
    if file_size == 0:
        raise HTTPException(status_code=500, detail="Backup file is empty")

    filename = os.path.basename(file_path)
    
    # Determine media type
    media_type = 'application/octet-stream'
    if filename.endswith('.gz'):
        media_type = 'application/gzip'
    elif filename.endswith('.sql'):
        media_type = 'application/sql'
    
    return FileResponse(
        path=file_path, 
        filename=filename, 
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.patch("/{job_id}/toggle")
async def toggle_job(
    job_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Enable or disable a job"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.is_active = not job.is_active
    db.commit()
    
    return {
        "success": True,
        "is_active": job.is_active,
        "message": f"Job {'enabled' if job.is_active else 'disabled'} successfully"
    }


# Job Execution Endpoints

@router.post("/{job_id}/execute")
@require_permission("jobs:execute")
async def execute_job(
    job_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Trigger manual job execution"""
    logger.info("manual_job_execution", job_id=job_id, user_id=current_user.id)
    
    try:
        job_manager = JobManager(db)
        execution = job_manager.execute_job(job_id, current_user.id, triggered_by='manual')
        
        return {
            "execution_id": execution.id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "message": "Job execution started"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("job_execution_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job_execution(
    job_id: int,
    execution_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a running job execution"""
    try:
        job_manager = JobManager(db)
        success = job_manager.cancel_execution(execution_id)
        
        return {
            "success": success,
            "message": "Job execution cancelled"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("cancel_execution_failed", execution_id=execution_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Job History & Logs

@router.get("/{job_id}/executions")
async def list_job_executions(
    job_id: int,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List job execution history"""
    # Verify job exists
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get executions
    query = db.query(JobExecution).filter(JobExecution.job_id == job_id)
    total = query.count()
    
    executions = query.order_by(JobExecution.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "executions": [
            {
                "id": exec.id,
                "status": exec.status,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration_ms": exec.duration_ms,
                "rows_processed": exec.rows_processed,
                "rows_affected": exec.rows_affected,
                "result": exec.result,
                "error_message": exec.error_message,
                "triggered_by": exec.triggered_by,
                "retry_count": exec.retry_count,
                "created_at": exec.created_at.isoformat()
            }
            for exec in executions
        ]
    }


@router.get("/{job_id}/executions/{execution_id}")
async def get_execution_details(
    job_id: int,
    execution_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed execution information"""
    execution = db.query(JobExecution).filter(
        JobExecution.id == execution_id,
        JobExecution.job_id == job_id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "id": execution.id,
        "job_id": execution.job_id,
        "status": execution.status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": execution.duration_ms,
        "result": execution.result,
        "rows_processed": execution.rows_processed,
        "rows_affected": execution.rows_affected,
        "error_message": execution.error_message,
        "error_stack_trace": execution.error_stack_trace,
        "execution_logs": execution.execution_logs,
        "resource_usage": execution.resource_usage,
        "retry_count": execution.retry_count,
        "is_retry": execution.is_retry,
        "triggered_by": execution.triggered_by,
        "triggered_by_user_id": execution.triggered_by_user_id,
        "created_at": execution.created_at.isoformat()
    }


@router.get("/{job_id}/executions/{execution_id}/logs")
async def get_execution_logs(
    job_id: int,
    execution_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get execution logs"""
    execution = db.query(JobExecution).filter(
        JobExecution.id == execution_id,
        JobExecution.job_id == job_id
    ).first()
    
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "execution_id": execution.id,
        "logs": execution.execution_logs or "",
        "error_message": execution.error_message,
        "error_stack_trace": execution.error_stack_trace
    }


# Stored Procedure Discovery

@router.get("/procedures/discover")
async def discover_procedures(
    connection_id: int,
    schema: str = 'public',
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Discover stored procedures and functions in a schema"""
    # Get connection
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        # Get connection string
        password = decrypt_value(connection.encrypted_password) if connection.encrypted_password else ""
        connection_string = connection.get_connection_string(password)
        
        # Discover procedures
        procedures = ProcedureExecutor.discover_procedures(connection_string, schema)
        
        return {"procedures": procedures}
        
    except Exception as e:
        logger.error("procedure_discovery_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/procedures/{procedure_name}/parameters")
async def get_procedure_parameters(
    procedure_name: str,
    connection_id: int,
    schema: str = 'public',
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get parameters for a specific procedure"""
    # Get connection
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        # Get connection string
        password = decrypt_value(connection.encrypted_password) if connection.encrypted_password else ""
        connection_string = connection.get_connection_string(password)
        
        # Get parameters
        parameters = ProcedureExecutor.get_procedure_parameters(
            connection_string,
            procedure_name,
            schema
        )
        
        return {"parameters": parameters}
        
    except Exception as e:
        logger.error("parameter_discovery_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Quick Backup

@router.post("/backup/quick")
@require_permission("jobs:backup")
async def quick_backup(
    request: QuickBackupRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Execute one-click database backup"""
    logger.info("quick_backup_request", connection_id=request.connection_id, user_id=current_user.id)
    
    try:
        # Create temporary job for backup
        job_data = {
            'name': f"Quick Backup - {request.database_name} - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'description': 'One-click database backup',
            'job_type': JobType.DATABASE_BACKUP.value,
            'connection_id': request.connection_id,
            'is_active': False,  # Don't schedule it
            'config': {
                'database_type': 'postgresql',  # TODO: Detect from connection
                'database_name': request.database_name,
                'backup_type': request.backup_type,
                'compression_enabled': request.compression_enabled,
                'retention_days': request.retention_days,
                'storage_path': request.storage_path,
                'format': request.format or 'custom'
            }
        }
        
        job_manager = JobManager(db)
        job = job_manager.create_job(job_data, current_user.id)
        
        # Execute immediately
        execution = job_manager.execute_job(job.id, current_user.id, triggered_by='manual')
        
        return {
            "job_id": job.id,
            "execution_id": execution.id,
            "status": execution.status,
            "result": execution.result,
            "message": "Backup completed successfully" if execution.status == JobStatus.COMPLETED.value else "Backup failed"
        }
        
    except Exception as e:
        logger.error("quick_backup_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Schedule Management

@router.get("/{job_id}/schedule/next-runs")
async def preview_next_runs(
    job_id: int,
    count: int = Query(5, le=20),
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Preview next N run times for a scheduled job"""
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.cron_expression:
        return {"next_runs": []}
    
    try:
        next_runs = JobScheduler.calculate_next_n_runs(
            job.cron_expression,
            count,
            job.timezone or 'UTC'
        )
        
        return {
            "next_runs": [run.isoformat() for run in next_runs]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/schedule/validate")
async def validate_cron(
    cron_expression: str,
    current_user: User = Depends(get_current_active_user)
):
    """Validate a cron expression"""
    is_valid, error = JobScheduler.validate_cron_expression(cron_expression)
    
    if not is_valid:
        return {
            "valid": False,
            "error": error
        }
    
    # Calculate next few runs as preview
    try:
        next_runs = JobScheduler.calculate_next_n_runs(cron_expression, 5)
        return {
            "valid": True,
            "next_runs": [run.isoformat() for run in next_runs]
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }



@router.get("/system/directories")
@require_permission("jobs:manage")
async def list_system_directories(
    path: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """List directories in the file system (restricted access)"""
    import os
    
    # Define allowed root paths
    ALLOWED_ROOTS = ['/app/backups', '/app/data', '/app/uploads', '/tmp']
    
    # If no path provided, list allowed roots
    if not path:
        return {
            "current_path": "/",
            "directories": [{"name": p, "path": p} for p in ALLOWED_ROOTS]
        }
    
    # Validate path is within allowed roots
    msg = "Access denied"
    is_allowed = False
    for root in ALLOWED_ROOTS:
        if path.startswith(root):
            is_allowed = True
            break
            
    if not is_allowed:
         # Also allow listing subdirectories of permitted paths, handled by startswith check above
         # But we must prevent traversal
         if '..' in path:
             raise HTTPException(status_code=403, detail="Invalid path traversal")
             
    if not is_allowed and path != "/": 
         # Special case: if path is just /, return roots again 
         if path == "/":
             return {
                "current_path": "/",
                "directories": [{"name": p, "path": p} for p in ALLOWED_ROOTS]
            }
         raise HTTPException(status_code=403, detail="Access denied to this path")

    try:
        if not os.path.exists(path):
             raise HTTPException(status_code=404, detail="Path not found")
             
        if not os.path.isdir(path):
             raise HTTPException(status_code=400, detail="Not a directory")
             
        # List directories
        items = os.listdir(path)
        directories = []
        
        for item in sorted(items):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                directories.append({
                    "name": item,
                    "path": full_path
                })
                
        return {
            "current_path": path,
            "parent_path": os.path.dirname(path) if path not in ALLOWED_ROOTS else "/",
            "directories": directories
        }
        
    except Exception as e:
        logger.error("directory_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/presets")
async def get_cron_presets(
    current_user: User = Depends(get_current_active_user)
):
    """Get common cron expression presets"""
    presets = [
        {"name": "Every 5 minutes", "value": "*/5 * * * *"},
        {"name": "Every 15 minutes", "value": "*/15 * * * *"},
        {"name": "Every 30 minutes", "value": "*/30 * * * *"},
        {"name": "Hourly", "value": "0 * * * *"},
        {"name": "Daily at midnight", "value": "0 0 * * *"},
        {"name": "Daily at 2 AM", "value": "0 2 * * *"},
        {"name": "Weekly (Sunday midnight)", "value": "0 0 * * 0"},
        {"name": "Weekly (Monday midnight)", "value": "0 0 * * 1"},
        {"name": "Monthly (1st at midnight)", "value": "0 0 1 * *"},
    ]
    
    return {"presets": presets}


def _get_active_jobs():
    """Helper to query active jobs in a thread-safe manner."""
    with get_app_db_context() as db:
        executions = db.query(JobExecution).filter(
            JobExecution.status.in_([JobStatus.RUNNING, JobStatus.PENDING])
        ).all()
        
        return [
            {
                "job_id": e.job_id,
                "execution_id": e.id,
                "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
                "start_time": e.started_at.isoformat() if e.started_at else None
            } for e in executions
        ]


@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Run DB query in a separate thread to avoid blocking the event loop
            try:
                active_jobs_data = await asyncio.to_thread(_get_active_jobs)
                await websocket.send_json({"active_jobs": active_jobs_data})
            except Exception as e:
                logger.error("websocket_db_error", error=str(e))
                await websocket.send_json({"error": str(e)})
            
            await asyncio.sleep(2)  # Poll every 2 seconds
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        try:
            await websocket.close()
        except: # noqa
            pass
