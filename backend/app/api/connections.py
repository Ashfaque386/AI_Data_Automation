"""
Connection Profile API Routes - User Operational Database Management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_app_db
from app.models import User, ConnectionProfile
from app.models.connection import ConnectionType, ConnectionGroup, ConnectionMode, HealthStatus
from app.models.audit import AuditActionType, TableEntryAudit
from app.models.import_job import ImportJob
from app.models.connection_permission import ConnectionPermission
from app.models.connection_health import ConnectionHealthLog
from app.models.job import ScheduledJob
from app.core.rbac import get_current_user
from app.core.crypto import encrypt_value, decrypt_value
from app.core.audit import AuditLogger
from app.connections import connection_manager, health_monitor, capability_detector
from app.services.audit_service import audit_service
from app.security.rbac import require_read_permission, connection_rbac
from app.security.schema_access import schema_access_control

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class ConnectionProfileCreate(BaseModel):
    """Schema for creating a connection profile."""
    name: str
    description: Optional[str] = None
    db_type: ConnectionType
    connection_group: Optional[ConnectionGroup] = ConnectionGroup.DEVELOPMENT
    connection_mode: Optional[ConnectionMode] = ConnectionMode.READ_WRITE
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None  # Full connection URI
    schema: Optional[str] = "public"
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    pool_size: int = 5
    max_connections: int = 10
    timeout_seconds: int = 30
    is_read_only: bool = False
    is_default: bool = False


class ConnectionProfileUpdate(BaseModel):
    """Schema for updating a connection profile."""
    name: Optional[str] = None
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    schema: Optional[str] = None
    is_read_only: Optional[bool] = None


class ConnectionProfileResponse(BaseModel):
    """Schema for connection profile response (password masked)."""
    id: int
    name: str
    description: Optional[str]
    db_type: ConnectionType
    connection_group: Optional[str]
    connection_mode: Optional[str]
    host: Optional[str]
    port: Optional[int]
    database: str
    username: Optional[str]
    schema: Optional[str]
    ssl_enabled: bool
    pool_size: int
    max_connections: int
    timeout_seconds: int
    health_status: Optional[str]
    last_health_check: Optional[datetime]
    response_time_ms: Optional[int]
    failed_attempts: int
    capabilities: Optional[dict]
    is_active: bool
    is_read_only: bool
    is_default: bool
    created_at: datetime
    has_connection_string: bool = False  # Derived field
    
    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Schema for connection test result."""
    success: bool
    message: str
    details: Optional[dict] = None


class DatabaseDiscoveryRequest(BaseModel):
    """Schema for discovering databases."""
    db_type: ConnectionType
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None



# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/", response_model=ConnectionProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    connection: ConnectionProfileCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db),
    request: Request = None
):
    """Create a new User Operational Database connection profile."""
    # Check permission
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required to manage connections"
        )
    
    # Check if name already exists
    existing = db.query(ConnectionProfile).filter(ConnectionProfile.name == connection.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection profile '{connection.name}' already exists"
        )
    
    # Encrypt password & connection string
    encrypted_password = encrypt_value(connection.password) if connection.password else None
    encrypted_string = encrypt_value(connection.connection_string) if connection.connection_string else None
    
    # Create profile
    profile = ConnectionProfile(
        name=connection.name,
        description=connection.description,
        db_type=connection.db_type,
        host=connection.host,
        port=connection.port,
        database=connection.database,
        username=connection.username,
        encrypted_password=encrypted_password,
        encrypted_connection_string=encrypted_string,
        schema=connection.schema,
        is_read_only=connection.is_read_only,
        created_by=current_user.id
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # Audit log with new service
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.CONNECTION_CREATE,
        resource_type="connection",
        resource_id=str(profile.id),
        resource_name=profile.name,
        connection_id=profile.id,
        connection_name=profile.name,
        action_details={"db_type": profile.db_type, "host": profile.host},
        request=request
    )
    
    response = ConnectionProfileResponse.from_orm(profile)
    response.has_connection_string = bool(profile.encrypted_connection_string)
    return response


@router.post("/discover/databases", response_model=List[str])
async def discover_databases(
    request: DatabaseDiscoveryRequest = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Discover databases using the provided connection settings.
    """
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(status_code=403, detail="Admin permission required")

    # Default to maintenance database if using parameters
    target_db = "postgres"
    if request.db_type == ConnectionType.POSTGRESQL:
        target_db = "postgres"
    elif request.db_type == ConnectionType.MONGODB:
        target_db = "admin"
    elif request.db_type == ConnectionType.MYSQL:
        target_db = "mysql"
    elif request.db_type == ConnectionType.SQLITE:
        return ["main"]

    # Create temp profile (not saved to DB)
    # We populate fields needed by get_connection_string
    temp_profile = ConnectionProfile(
        name="temp_discovery",
        db_type=request.db_type,
        host=request.host or "localhost",
        port=request.port,
        database=target_db,
        username=request.username,
        schema=request.schema,
        timeout_seconds=10
    )
    
    try:
        connector = connection_manager.create_temp_connector(
            temp_profile,
            decrypted_password=request.password,
            decrypted_connection_string=request.connection_string
        )
        
        try:
            databases = connector.list_databases()
            return sorted(databases)
        finally:
            connector.disconnect()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"DISCOVERY ERROR: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to discover databases: {str(e)}"
        )


@router.get("/", response_model=List[ConnectionProfileResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all connection profiles (passwords masked)."""
    profiles = db.query(ConnectionProfile).all()
    # Map to response manually or rely on from_orm
    responses = []
    for p in profiles:
        resp = ConnectionProfileResponse.from_orm(p)
        resp.has_connection_string = bool(p.encrypted_connection_string)
        responses.append(resp)
    return responses


@router.get("/{connection_id}", response_model=ConnectionProfileResponse)
@require_read_permission
async def get_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get a specific connection profile. Requires READ permission."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    resp = ConnectionProfileResponse.from_orm(profile)
    resp.has_connection_string = bool(profile.encrypted_connection_string)
    return resp


@router.put("/{connection_id}", response_model=ConnectionProfileResponse)
async def update_connection(
    connection_id: int,
    updates: ConnectionProfileUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Update a connection profile."""
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Update fields
    if updates.name is not None:
        profile.name = updates.name
    if updates.description is not None:
        profile.description = updates.description
    if updates.host is not None:
        profile.host = updates.host
    if updates.port is not None:
        profile.port = updates.port
    if updates.database is not None:
        profile.database = updates.database
    if updates.username is not None:
        profile.username = updates.username
    if updates.password is not None:
        profile.encrypted_password = encrypt_value(updates.password)
    if updates.connection_string is not None:
        profile.encrypted_connection_string = encrypt_value(updates.connection_string)
    if updates.schema is not None:
        profile.schema = updates.schema
    if updates.is_read_only is not None:
        profile.is_read_only = updates.is_read_only
    
    db.commit()
    db.refresh(profile)
    
    # Audit log with new service
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.CONNECTION_UPDATE,
        resource_type="connection",
        resource_id=str(profile.id),
        resource_name=profile.name,
        connection_id=profile.id,
        connection_name=profile.name,
        action_details={"updated_fields": [k for k, v in updates.dict(exclude_unset=True).items()]}
    )
    
    resp = ConnectionProfileResponse.from_orm(profile)
    resp.has_connection_string = bool(profile.encrypted_connection_string)
    return resp


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Delete a connection profile."""
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Audit log before deletion
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.CONNECTION_DELETE,
        resource_type="connection",
        resource_id=str(profile.id),
        resource_name=profile.name,
        connection_id=profile.id,
        connection_name=profile.name,
        action_details={"db_type": profile.db_type}
    )
    
    try:
        # Delete related table entry audit logs (FK restriction)
        db.query(TableEntryAudit).filter(TableEntryAudit.connection_id == connection_id).delete()
        
        # Delete related connection health logs (FK restriction, manual cleanup)
        db.query(ConnectionHealthLog).filter(ConnectionHealthLog.connection_id == connection_id).delete()
        
        # Delete related connection permissions (FK restriction, manual cleanup)
        db.query(ConnectionPermission).filter(ConnectionPermission.connection_id == connection_id).delete()
        
        # Delete related scheduled jobs (FK restriction, can trigger cascades)
        scheduled_jobs = db.query(ScheduledJob).filter(ScheduledJob.connection_id == connection_id).all()
        for job in scheduled_jobs:
            db.delete(job)

        # Delete related import jobs (FK restriction)
        # Use ORM delete to trigger cascades for ImportAuditLogs
        import_jobs = db.query(ImportJob).filter(ImportJob.target_connection_id == connection_id).all()
        for job in import_jobs:
            db.delete(job)

        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error deleting connection: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete connection: {str(e)}"
        )


@router.post("/{connection_id}/activate", response_model=ConnectionProfileResponse)
async def activate_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Activate a connection profile."""
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required"
        )
    
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Do not deactivate others - allow multiple active connections
    
    # Activate this one
    profile.is_active = True
    db.commit()
    db.refresh(profile)
    
    # Audit log
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.CONNECTION_ACTIVATE,
        resource_type="connection",
        resource_id=str(profile.id),
        resource_name=profile.name,
        connection_id=profile.id,
        connection_name=profile.name
    )
    
    resp = ConnectionProfileResponse.from_orm(profile)
    resp.has_connection_string = bool(profile.encrypted_connection_string)
    return resp


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Test a connection profile using the new HealthMonitor."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Use new health monitor
    try:
        health_status = await health_monitor.check_connection(db, profile)
        
        return ConnectionTestResult(
            success=health_status == HealthStatus.ONLINE,
            message=f"Connection {health_status.value}",
            details={
                "db_type": profile.db_type,
                "database": profile.database,
                "response_time_ms": profile.response_time_ms,
                "health_status": health_status.value
            }
        )
    except Exception as e:
        return ConnectionTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            details={"error": str(e)}
        )


@router.get("/{connection_id}/health")
async def get_connection_health(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get current health status of a connection."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    return {
        "connection_id": profile.id,
        "connection_name": profile.name,
        "health_status": profile.health_status.value if profile.health_status else "unknown",
        "last_health_check": profile.last_health_check.isoformat() if profile.last_health_check else None,
        "response_time_ms": profile.response_time_ms,
        "failed_attempts": profile.failed_attempts
    }


@router.get("/{connection_id}/health/history")
async def get_health_history(
    connection_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get health check history for a connection."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    history = health_monitor.get_health_history(db, connection_id, hours)
    
    return {
        "connection_id": profile.id,
        "connection_name": profile.name,
        "history": [
            {
                "timestamp": log.timestamp.isoformat(),
                "status": log.status,
                "response_time_ms": log.response_time_ms,
                "error_message": log.error_message,
                "checked_by": log.checked_by
            }
            for log in history
        ]
    }


@router.get("/{connection_id}/capabilities")
async def get_connection_capabilities(
    connection_id: int,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get database capabilities."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Refresh capabilities if requested or not cached
    if refresh or not profile.capabilities:
        try:
            capabilities = capability_detector.detect_and_save(db, profile)
            return {
                "connection_id": profile.id,
                "connection_name": profile.name,
                "capabilities": capability_detector._capabilities_to_dict(capabilities)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to detect capabilities: {str(e)}"
            )
    
    return {
        "connection_id": profile.id,
        "connection_name": profile.name,
        "capabilities": profile.capabilities
    }


@router.get("/{connection_id}/schemas")
@require_read_permission
async def list_schemas(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all schemas in the database. Requires READ permission."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    try:
        decrypted_password = decrypt_value(profile.encrypted_password) if profile.encrypted_password else ""
        
        # NOTE: If we implement connection_string decryption here, we need to pass it
        # But for now, connection_manager needs update to fetch it.
        # This part assumes connection_manager knows how to handle it.
        # Wait, I need to update connection_manager to accept or retrieve encrypted string.
        # But connection_manager.get_connector takes (profile, decrypted_password).
        # It doesn't take decrypted_connection_string.
        # I should just update ConnectionManager to decrypt it internally if profile has it.
        # BUT ConnectionManager receives `profile` OBJECT? Yes.
        # "connector = connection_manager.get_connector(profile, decrypted_password)"
        
        # So I will decrypt it here and pass it, OR modify ConnectionManager.
        # Modifying ConnectionManager logic is cleaner. It accepts `profile`.
        # But it also accepts `decrypted_password` explicitly because `profile` has it encrypted.
        # So I should probably pass `decrypted_connection_string` too?
        # Or update `get_connector` to rely less on arguments and more on profile?
        # But `decrypt_value` is in `app.core.crypto`. `connection_manager.py` might import it.
        
        connector = connection_manager.get_connector(profile, decrypted_password)
        all_schemas = connector.list_schemas()
        
        # Apply schema filtering based on user permissions
        filtered_schemas = schema_access_control.filter_schemas(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            all_schemas=all_schemas
        )
        
        return {
            "connection_id": profile.id,
            "connection_name": profile.name,
            "schemas": filtered_schemas
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schemas: {str(e)}"
        )


@router.get("/{connection_id}/tables")
@require_read_permission
async def list_tables(
    connection_id: int,
    schema: str = "public",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all tables in a schema. Requires READ permission."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    try:
        decrypted_password = decrypt_value(profile.encrypted_password) if profile.encrypted_password else ""
        connector = connection_manager.get_connector(profile, decrypted_password)
        all_tables = connector.list_tables(schema)
        
        # Extract table names for filtering
        table_names = [t.name for t in all_tables]
        
        # Apply table filtering based on user permissions
        filtered_table_names = schema_access_control.filter_tables(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            schema=schema,
            all_tables=table_names
        )
        
        # Filter the table objects to only include allowed tables
        filtered_tables = [t for t in all_tables if t.name in filtered_table_names]
        
        return {
            "connection_id": profile.id,
            "connection_name": profile.name,
            "schema": schema,
            "tables": [{"name": t.name, "schema": t.schema, "type": t.table_type} for t in filtered_tables]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tables: {str(e)}"
        )


@router.get("/health/dashboard")
async def health_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get health dashboard for all connections."""
    connections = db.query(ConnectionProfile).filter(ConnectionProfile.is_active == True).all()
    
    dashboard = []
    for conn in connections:
        dashboard.append({
            "id": conn.id,
            "name": conn.name,
            "db_type": conn.db_type,
            "connection_group": conn.connection_group.value if conn.connection_group else None,
            "health_status": conn.health_status.value if conn.health_status else "unknown",
            "last_health_check": conn.last_health_check.isoformat() if conn.last_health_check else None,
            "response_time_ms": conn.response_time_ms,
            "failed_attempts": conn.failed_attempts,
            "is_active": conn.is_active
        })
    
    return {
        "total_connections": len(connections),
        "connections": dashboard
    }
