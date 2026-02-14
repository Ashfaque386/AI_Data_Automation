"""
Connection Permissions API
Manage user permissions for database connections
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_app_db
from app.models.user import User
from app.models.connection_permission import ConnectionPermission
from app.models.connection import ConnectionProfile
from app.models.audit import AuditActionType
from app.core.rbac import get_current_user
from app.services.audit_service import audit_service
from app.security.rbac import connection_rbac


router = APIRouter()


# Pydantic models
class PermissionGrantRequest(BaseModel):
    user_id: int
    can_read: bool = True
    can_write: bool = False
    can_execute_ddl: bool = False
    allowed_schemas: List[str] = None
    denied_tables: List[str] = None


class PermissionResponse(BaseModel):
    id: int
    connection_id: int
    user_id: int
    user_email: str
    can_read: bool
    can_write: bool
    can_execute_ddl: bool
    allowed_schemas: List[str] = None
    denied_tables: List[str] = None
    
    class Config:
        from_attributes = True


@router.post("/{connection_id}/permissions", response_model=PermissionResponse)
async def grant_permission(
    connection_id: int,
    request: PermissionGrantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """
    Grant permission to a user for a connection
    Requires admin permission
    """
    # Check if current user is admin
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required to manage permissions"
        )
    
    # Check if connection exists
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    # Check if target user exists
    target_user = db.query(User).filter(User.id == request.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if permission already exists
    existing = db.query(ConnectionPermission).filter(
        ConnectionPermission.connection_id == connection_id,
        ConnectionPermission.user_id == request.user_id
    ).first()
    
    if existing:
        # Update existing permission
        existing.can_read = request.can_read
        existing.can_write = request.can_write
        existing.can_execute_ddl = request.can_execute_ddl
        existing.allowed_schemas = request.allowed_schemas
        existing.denied_tables = request.denied_tables
        permission = existing
    else:
        # Create new permission
        permission = ConnectionPermission(
            connection_id=connection_id,
            user_id=request.user_id,
            can_read=request.can_read,
            can_write=request.can_write,
            can_execute_ddl=request.can_execute_ddl,
            allowed_schemas=request.allowed_schemas,
            denied_tables=request.denied_tables
        )
        db.add(permission)
    
    db.commit()
    db.refresh(permission)
    
    # Audit log
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.PERMISSION_GRANT,
        resource_type="permission",
        resource_id=str(permission.id),
        connection_id=connection_id,
        connection_name=connection.name,
        action_details={
            "target_user_id": request.user_id,
            "target_user_email": target_user.email,
            "can_read": request.can_read,
            "can_write": request.can_write,
            "can_execute_ddl": request.can_execute_ddl
        }
    )
    
    # Add user_email to response
    permission.user_email = target_user.email
    
    return permission


@router.delete("/{connection_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_permission(
    connection_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """
    Revoke all permissions for a user on a connection
    Requires admin permission
    """
    # Check if current user is admin
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required to manage permissions"
        )
    
    # Find permission
    permission = db.query(ConnectionPermission).filter(
        ConnectionPermission.connection_id == connection_id,
        ConnectionPermission.user_id == user_id
    ).first()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Get connection and user for audit log
    connection = db.query(ConnectionProfile).filter(ConnectionProfile.id == connection_id).first()
    target_user = db.query(User).filter(User.id == user_id).first()
    
    # Audit log before deletion
    await audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action_type=AuditActionType.PERMISSION_REVOKE,
        resource_type="permission",
        resource_id=str(permission.id),
        connection_id=connection_id,
        connection_name=connection.name if connection else None,
        action_details={
            "target_user_id": user_id,
            "target_user_email": target_user.email if target_user else None
        }
    )
    
    db.delete(permission)
    db.commit()


@router.get("/{connection_id}/permissions", response_model=List[PermissionResponse])
async def list_connection_permissions(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """
    List all permissions for a connection
    Requires admin permission
    """
    # Check if current user is admin
    if not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required to view permissions"
        )
    
    # Get all permissions for connection
    permissions = db.query(ConnectionPermission).filter(
        ConnectionPermission.connection_id == connection_id
    ).all()
    
    # Add user emails
    result = []
    for perm in permissions:
        user = db.query(User).filter(User.id == perm.user_id).first()
        perm.user_email = user.email if user else "Unknown"
        result.append(perm)
    
    return result


@router.get("/users/{user_id}/connection-permissions", response_model=List[PermissionResponse])
async def list_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """
    List all connection permissions for a user
    Users can view their own permissions, admins can view any user's permissions
    """
    # Check if user is viewing their own permissions or is admin
    if current_user.id != user_id and not current_user.has_permission("admin:manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own permissions"
        )
    
    # Get all permissions for user
    permissions = db.query(ConnectionPermission).filter(
        ConnectionPermission.user_id == user_id
    ).all()
    
    # Add user email
    user = db.query(User).filter(User.id == user_id).first()
    user_email = user.email if user else "Unknown"
    
    for perm in permissions:
        perm.user_email = user_email
    
    return permissions
