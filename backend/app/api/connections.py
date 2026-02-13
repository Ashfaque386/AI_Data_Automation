"""
Connection Profile API Routes - User Operational Database Management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_app_db
from app.models import User, ConnectionProfile
from app.core.rbac import get_current_user
from app.core.crypto import encrypt_value, decrypt_value
from app.core.audit import AuditLogger

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class ConnectionProfileCreate(BaseModel):
    """Schema for creating a connection profile."""
    name: str
    description: Optional[str] = None
    db_type: str  # postgresql, mysql, oracle, mssql, sqlite, duckdb
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    schema: Optional[str] = None
    is_read_only: bool = False


class ConnectionProfileUpdate(BaseModel):
    """Schema for updating a connection profile."""
    name: Optional[str] = None
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    schema: Optional[str] = None
    is_read_only: Optional[bool] = None


class ConnectionProfileResponse(BaseModel):
    """Schema for connection profile response (password masked)."""
    id: int
    name: str
    description: Optional[str]
    db_type: str
    host: Optional[str]
    port: Optional[int]
    database: str
    username: Optional[str]
    schema: Optional[str]
    is_active: bool
    is_read_only: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Schema for connection test result."""
    success: bool
    message: str
    details: Optional[dict] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/", response_model=ConnectionProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    connection: ConnectionProfileCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
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
    
    # Encrypt password
    encrypted_password = encrypt_value(connection.password) if connection.password else None
    
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
        schema=connection.schema,
        is_read_only=connection.is_read_only,
        created_by=current_user.id
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="create_connection",
        user=current_user,
        resource_type="connection",
        resource_id=profile.id,
        details={"name": profile.name, "db_type": profile.db_type}
    )
    
    return profile


@router.get("/", response_model=List[ConnectionProfileResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all connection profiles (passwords masked)."""
    profiles = db.query(ConnectionProfile).all()
    return profiles


@router.get("/{connection_id}", response_model=ConnectionProfileResponse)
async def get_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get a specific connection profile."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    return profile


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
    if updates.schema is not None:
        profile.schema = updates.schema
    if updates.is_read_only is not None:
        profile.is_read_only = updates.is_read_only
    
    db.commit()
    db.refresh(profile)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="update_connection",
        user=current_user,
        resource_type="connection",
        resource_id=profile.id,
        details={"name": profile.name}
    )
    
    return profile


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
    auditor = AuditLogger(db)
    auditor.log(
        action="delete_connection",
        user=current_user,
        resource_type="connection",
        resource_id=profile.id,
        details={"name": profile.name}
    )
    
    db.delete(profile)
    db.commit()


@router.post("/{connection_id}/activate", response_model=ConnectionProfileResponse)
async def activate_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Activate a connection profile (deactivates all others)."""
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
    
    # Deactivate all others
    db.query(ConnectionProfile).update({"is_active": False})
    
    # Activate this one
    profile.is_active = True
    db.commit()
    db.refresh(profile)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="activate_connection",
        user=current_user,
        resource_type="connection",
        resource_id=profile.id,
        details={"name": profile.name}
    )
    
    return profile


@router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Test a connection profile."""
    profile = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection profile not found"
        )
    
    # Decrypt password and create connection string
    decrypted_password = decrypt_value(profile.encrypted_password) if profile.encrypted_password else ""
    connection_string = profile.get_connection_string(decrypted_password)
    
    # Test connection
    try:
        from sqlalchemy import create_engine
        test_engine = create_engine(connection_string, connect_args={'connect_timeout': 5})
        
        with test_engine.connect() as conn:
            # Simple test query
            result = conn.execute("SELECT 1")
            result.fetchone()
        
        test_engine.dispose()
        
        return ConnectionTestResult(
            success=True,
            message="Connection successful",
            details={"db_type": profile.db_type, "database": profile.database}
        )
    except Exception as e:
        return ConnectionTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            details={"error": str(e)}
        )
