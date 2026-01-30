"""
Authentication API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.schemas import (
    UserCreate, UserResponse, Token, LoginRequest, 
    RefreshTokenRequest, PasswordChange
)
from app.models import User, Role
from app.core.auth import (
    authenticate_user, create_tokens, refresh_access_token,
    get_user_by_email
)
from app.core.rbac import get_current_user
from app.core.audit import AuditLogger

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    existing = get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check username
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=User.hash_password(user_data.password)
    )
    
    # Assign roles
    if user_data.role_ids:
        roles = db.query(Role).filter(Role.id.in_(user_data.role_ids)).all()
        user.roles = roles
    else:
        # Default to viewer role
        default_role = db.query(Role).filter(Role.name == "viewer").first()
        if default_role:
            user.roles = [default_role]
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="user_register",
        user=user,
        resource_type="user",
        resource_id=str(user.id)
    )
    
    return user


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    tokens = create_tokens(user, db)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_login(user, success=True)
    
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    tokens = refresh_access_token(db, request.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return tokens


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout and revoke refresh token."""
    # In a full implementation, we'd revoke the specific token
    # For now, just log the action
    auditor = AuditLogger(db)
    auditor.log(
        action="logout",
        user=current_user,
        resource_type="auth"
    )
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/password", response_model=dict)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = User.hash_password(password_data.new_password)
    db.commit()
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="password_change",
        user=current_user,
        resource_type="user",
        resource_id=str(current_user.id)
    )
    
    return {"message": "Password changed successfully"}
