"""
Users API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas import UserResponse, UserUpdate, RoleResponse, RoleCreate
from app.models import User, Role
from app.core.rbac import get_current_user, get_current_superuser

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID."""
    # Users can view their own profile; admins can view anyone
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user."""
    # Users can update themselves; admins can update anyone
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update fields
    if user_update.email:
        user.email = user_update.email
    if user_update.username:
        user.username = user_update.username
    if user_update.full_name:
        user.full_name = user_update.full_name
    
    # Only admins can change active status and roles
    if current_user.is_superuser:
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        if user_update.role_ids:
            roles = db.query(Role).filter(Role.id.in_(user_update.role_ids)).all()
            user.roles = roles
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/roles/", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all roles."""
    roles = db.query(Role).all()
    return roles


@router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Create a new role (admin only)."""
    existing = db.query(Role).filter(Role.name == role_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already exists"
        )
    
    role = Role(
        name=role_data.name,
        description=role_data.description
    )
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    return role
