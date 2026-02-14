"""
Connection RBAC Service
Permission checking and enforcement for database connections
"""
from functools import wraps
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.connection_permission import ConnectionPermission
from app.models.user import User
from app.models.connection import ConnectionProfile


class ConnectionRBAC:
    """Service for checking and managing connection permissions"""
    
    @staticmethod
    def check_read_permission(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> bool:
        """Check if user has READ permission for connection"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admin users have all permissions
        if user.has_permission("admin:manage"):
            return True
        
        # Check specific permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id,
            ConnectionPermission.can_read == True
        ).first()
        
        return permission is not None
    
    @staticmethod
    def check_write_permission(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> bool:
        """Check if user has WRITE permission for connection"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admin users have all permissions
        if user.has_permission("admin:manage"):
            return True
        
        # Check specific permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id,
            ConnectionPermission.can_write == True
        ).first()
        
        return permission is not None
    
    @staticmethod
    def check_execute_permission(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> bool:
        """Check if user has EXECUTE (DDL) permission for connection"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admin users have all permissions
        if user.has_permission("admin:manage"):
            return True
        
        # Check specific permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id,
            ConnectionPermission.can_execute_ddl == True
        ).first()
        
        return permission is not None
    
    @staticmethod
    def has_any_permission(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> bool:
        """Check if user has any permission for connection"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admin users have all permissions
        if user.has_permission("admin:manage"):
            return True
        
        # Check if user has any permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        return permission is not None
    
    @staticmethod
    def get_user_connections(
        db: Session,
        user_id: int,
        require_write: bool = False
    ) -> List[ConnectionProfile]:
        """
        Get all connections user has access to
        
        Args:
            db: Database session
            user_id: ID of the user
            require_write: If True, only return connections with write permission
        
        Returns:
            List of ConnectionProfile objects
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # Admin users see all connections
        if user.has_permission("admin:manage"):
            return db.query(ConnectionProfile).all()
        
        # Get connections with permissions
        query = db.query(ConnectionProfile).join(
            ConnectionPermission,
            ConnectionProfile.id == ConnectionPermission.connection_id
        ).filter(
            ConnectionPermission.user_id == user_id
        )
        
        if require_write:
            query = query.filter(ConnectionPermission.can_write == True)
        
        return query.distinct().all()
    
    @staticmethod
    def get_user_permissions(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> Dict[str, bool]:
        """Get all permissions a user has for a specific connection"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"can_read": False, "can_write": False, "can_execute_ddl": False}
        
        # Admin users have all permissions
        if user.has_permission("admin:manage"):
            return {"can_read": True, "can_write": True, "can_execute_ddl": True}
        
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return {"can_read": False, "can_write": False, "can_execute_ddl": False}
        
        return {
            "can_read": permission.can_read,
            "can_write": permission.can_write,
            "can_execute_ddl": permission.can_execute_ddl
        }


def require_read_permission(func):
    """Decorator to check READ permission"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        connection_id = kwargs.get('connection_id')
        current_user = kwargs.get('current_user')
        db = kwargs.get('db')
        
        if not connection_id or not current_user or not db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )
        
        rbac = ConnectionRBAC()
        if not rbac.check_read_permission(db, current_user.id, connection_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have READ permission for this connection"
            )
        
        return await func(*args, **kwargs)
    return wrapper


def require_write_permission(func):
    """Decorator to check WRITE permission"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        connection_id = kwargs.get('connection_id')
        current_user = kwargs.get('current_user')
        db = kwargs.get('db')
        
        if not connection_id or not current_user or not db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )
        
        rbac = ConnectionRBAC()
        if not rbac.check_write_permission(db, current_user.id, connection_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have WRITE permission for this connection"
            )
        
        return await func(*args, **kwargs)
    return wrapper


# Global RBAC instance
connection_rbac = ConnectionRBAC()
