"""
Role-Based Access Control (RBAC) Service
"""
from functools import wraps
from typing import List, Optional, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Role, Permission, Dataset, DatasetPermission
from app.core.auth import verify_token, get_user_by_id

security = HTTPBearer()


class PermissionDeniedError(HTTPException):
    """Permission denied exception."""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthorizedError(HTTPException):
    """Unauthorized exception."""
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise UnauthorizedError("Invalid or expired token")
    
    user = get_user_by_id(db, payload.sub)
    if not user:
        raise UnauthorizedError("User not found")
    
    if not user.is_active:
        raise UnauthorizedError("User account is disabled")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure current user is active."""
    if not current_user.is_active:
        raise PermissionDeniedError("Inactive user")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure current user is a superuser."""
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser access required")
    return current_user


def require_permission(permission_name: str):
    """Decorator to require a specific permission."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not current_user.has_permission(permission_name):
                raise PermissionDeniedError(f"Permission '{permission_name}' required")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_permissions(permission_names: List[str], require_all: bool = True):
    """Decorator to require multiple permissions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if require_all:
                for perm in permission_names:
                    if not current_user.has_permission(perm):
                        raise PermissionDeniedError(f"Permission '{perm}' required")
            else:
                if not any(current_user.has_permission(perm) for perm in permission_names):
                    raise PermissionDeniedError(f"One of permissions {permission_names} required")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


class DatasetAccessChecker:
    """Check user access to datasets."""
    
    @staticmethod
    def can_read(db: Session, user: User, dataset: Dataset) -> bool:
        """Check if user can read dataset."""
        if user.is_superuser:
            return True
        if dataset.owner_id == user.id:
            return True
        if dataset.is_public:
            return True
        
        # Check explicit permissions
        perm = db.query(DatasetPermission).filter(
            DatasetPermission.dataset_id == dataset.id,
            DatasetPermission.user_id == user.id,
            DatasetPermission.can_read == True
        ).first()
        
        if perm:
            return True
        
        # Check role-based permissions
        for role in user.roles:
            perm = db.query(DatasetPermission).filter(
                DatasetPermission.dataset_id == dataset.id,
                DatasetPermission.role_id == role.id,
                DatasetPermission.can_read == True
            ).first()
            if perm:
                return True
        
        return False
    
    @staticmethod
    def can_write(db: Session, user: User, dataset: Dataset) -> bool:
        """Check if user can write to dataset."""
        if user.is_superuser:
            return True
        if dataset.owner_id == user.id:
            return True
        if dataset.is_locked:
            return False
        
        perm = db.query(DatasetPermission).filter(
            DatasetPermission.dataset_id == dataset.id,
            DatasetPermission.user_id == user.id,
            DatasetPermission.can_write == True
        ).first()
        
        return perm is not None
    
    @staticmethod
    def can_delete(db: Session, user: User, dataset: Dataset) -> bool:
        """Check if user can delete dataset."""
        if user.is_superuser:
            return True
        if dataset.owner_id == user.id:
            return True
        
        perm = db.query(DatasetPermission).filter(
            DatasetPermission.dataset_id == dataset.id,
            DatasetPermission.user_id == user.id,
            DatasetPermission.can_delete == True
        ).first()
        
        return perm is not None
    
    @staticmethod
    def get_visible_columns(db: Session, user: User, dataset: Dataset) -> Optional[List[str]]:
        """Get list of visible columns for user. None means all visible."""
        if user.is_superuser or dataset.owner_id == user.id:
            return None
        
        perm = db.query(DatasetPermission).filter(
            DatasetPermission.dataset_id == dataset.id,
            DatasetPermission.user_id == user.id
        ).first()
        
        if perm and perm.visible_columns:
            return perm.visible_columns
        
        return None


# Default permissions for initialization
DEFAULT_PERMISSIONS = [
    # Dataset permissions
    {"name": "dataset:read", "resource": "dataset", "action": "read", "description": "Read datasets"},
    {"name": "dataset:write", "resource": "dataset", "action": "write", "description": "Write datasets"},
    {"name": "dataset:delete", "resource": "dataset", "action": "delete", "description": "Delete datasets"},
    {"name": "dataset:share", "resource": "dataset", "action": "share", "description": "Share datasets"},
    # SQL permissions
    {"name": "sql:execute", "resource": "sql", "action": "execute", "description": "Execute SQL queries"},
    {"name": "sql:write", "resource": "sql", "action": "write", "description": "Execute write SQL queries"},
    # Export permissions
    {"name": "export:excel", "resource": "export", "action": "excel", "description": "Export to Excel"},
    {"name": "export:csv", "resource": "export", "action": "csv", "description": "Export to CSV"},
    {"name": "export:json", "resource": "export", "action": "json", "description": "Export to JSON"},
    # Import permissions
    {"name": "import:execute", "resource": "import", "action": "execute", "description": "Execute data imports"},
    {"name": "import:view", "resource": "import", "action": "view", "description": "View import jobs and history"},
    {"name": "import:configure", "resource": "import", "action": "configure", "description": "Configure import mappings"},
    # Admin permissions
    {"name": "admin:users", "resource": "admin", "action": "users", "description": "Manage users"},
    {"name": "admin:roles", "resource": "admin", "action": "roles", "description": "Manage roles"},
    {"name": "admin:audit", "resource": "admin", "action": "audit", "description": "View audit logs"},
    {"name": "admin:jobs", "resource": "admin", "action": "jobs", "description": "Manage jobs"},
]

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Full system administrator",
        "is_system": True,
        "permissions": ["dataset:read", "dataset:write", "dataset:delete", "dataset:share",
                       "sql:execute", "sql:write", "export:excel", "export:csv", "export:json",
                       "import:execute", "import:view", "import:configure",
                       "admin:users", "admin:roles", "admin:audit", "admin:jobs"]
    },
    {
        "name": "analyst",
        "description": "Data analyst with read and SQL access",
        "is_system": True,
        "permissions": ["dataset:read", "sql:execute", "export:excel", "export:csv", "export:json",
                       "import:view"]
    },
    {
        "name": "viewer",
        "description": "Read-only access",
        "is_system": True,
        "permissions": ["dataset:read"]
    },
    {
        "name": "editor",
        "description": "Can read, write, and export data",
        "is_system": True,
        "permissions": ["dataset:read", "dataset:write", "sql:execute", "export:excel", "export:csv",
                       "import:execute", "import:view", "import:configure"]
    }
]


def initialize_rbac(db: Session):
    """Initialize default roles and permissions."""
    # Create permissions
    for perm_data in DEFAULT_PERMISSIONS:
        existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
        if not existing:
            perm = Permission(**perm_data)
            db.add(perm)
    
    db.commit()
    
    # Create roles with permissions
    for role_data in DEFAULT_ROLES:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(
                name=role_data["name"],
                description=role_data["description"],
                is_system=role_data["is_system"]
            )
            for perm_name in role_data["permissions"]:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    role.permissions.append(perm)
            db.add(role)
    
    db.commit()
