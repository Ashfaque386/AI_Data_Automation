"""
Schema Access Control Service
Filter schemas and tables based on user permissions
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.connection_permission import ConnectionPermission
from app.models.user import User


class SchemaAccessControl:
    """Service for filtering schemas and tables based on permissions"""
    
    @staticmethod
    def filter_schemas(
        db: Session,
        user_id: int,
        connection_id: int,
        all_schemas: List[str]
    ) -> List[str]:
        """
        Filter schemas based on user permissions
        
        Args:
            db: Database session
            user_id: ID of the user
            connection_id: ID of the connection
            all_schemas: List of all available schemas
        
        Returns:
            List of schemas the user can access
        """
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.has_permission("admin:manage"):
            return all_schemas  # Admins see everything
        
        # Get user permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return []  # No permission = no access
        
        # If allowed_schemas is None or empty, user can see all schemas
        if not permission.allowed_schemas:
            return all_schemas
        
        # Return only allowed schemas
        return [s for s in all_schemas if s in permission.allowed_schemas]
    
    @staticmethod
    def filter_tables(
        db: Session,
        user_id: int,
        connection_id: int,
        schema: str,
        all_tables: List[str]
    ) -> List[str]:
        """
        Filter tables based on user permissions
        
        Args:
            db: Database session
            user_id: ID of the user
            connection_id: ID of the connection
            schema: Schema name
            all_tables: List of all available tables in the schema
        
        Returns:
            List of tables the user can access
        """
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.has_permission("admin:manage"):
            return all_tables  # Admins see everything
        
        # Get user permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return []  # No permission = no access
        
        # Check if user has access to this schema
        if permission.allowed_schemas and schema not in permission.allowed_schemas:
            return []  # User doesn't have access to this schema
        
        # If denied_tables is None or empty, user can see all tables
        if not permission.denied_tables:
            return all_tables
        
        # Filter out denied tables (support both 'table' and 'schema.table' formats)
        filtered_tables = []
        for table in all_tables:
            # Check both plain table name and schema.table format
            if table not in permission.denied_tables and f"{schema}.{table}" not in permission.denied_tables:
                filtered_tables.append(table)
        
        return filtered_tables
    
    @staticmethod
    def can_access_schema(
        db: Session,
        user_id: int,
        connection_id: int,
        schema: str
    ) -> bool:
        """
        Check if user can access a specific schema
        
        Args:
            db: Database session
            user_id: ID of the user
            connection_id: ID of the connection
            schema: Schema name
        
        Returns:
            True if user can access the schema, False otherwise
        """
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.has_permission("admin:manage"):
            return True
        
        # Get user permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return False
        
        # If allowed_schemas is None or empty, user can access all schemas
        if not permission.allowed_schemas:
            return True
        
        # Check if schema is in allowed list
        return schema in permission.allowed_schemas
    
    @staticmethod
    def can_access_table(
        db: Session,
        user_id: int,
        connection_id: int,
        schema: str,
        table: str
    ) -> bool:
        """
        Check if user can access a specific table
        
        Args:
            db: Database session
            user_id: ID of the user
            connection_id: ID of the connection
            schema: Schema name
            table: Table name
        
        Returns:
            True if user can access the table, False otherwise
        """
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.has_permission("admin:manage"):
            return True
        
        # Get user permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return False
        
        # Check schema access first
        if permission.allowed_schemas and schema not in permission.allowed_schemas:
            return False
        
        # Check table denial (support both 'table' and 'schema.table' formats)
        if permission.denied_tables:
            if table in permission.denied_tables or f"{schema}.{table}" in permission.denied_tables:
                return False
        
        return True
    
    @staticmethod
    def get_accessible_schemas(
        db: Session,
        user_id: int,
        connection_id: int
    ) -> Optional[List[str]]:
        """
        Get list of schemas user can access
        
        Args:
            db: Database session
            user_id: ID of the user
            connection_id: ID of the connection
        
        Returns:
            List of accessible schemas, or None if user can access all schemas
        """
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.has_permission("admin:manage"):
            return None  # None means all schemas
        
        # Get user permission
        permission = db.query(ConnectionPermission).filter(
            ConnectionPermission.user_id == user_id,
            ConnectionPermission.connection_id == connection_id
        ).first()
        
        if not permission:
            return []
        
        # Return allowed_schemas (None means all, empty list means none)
        return permission.allowed_schemas


# Global instance
schema_access_control = SchemaAccessControl()
