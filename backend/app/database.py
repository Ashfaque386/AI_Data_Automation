"""
Database connection and session management - DUAL DATABASE ARCHITECTURE
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Optional
import duckdb
import os

from app.config import settings

# ============================================================================
# APPLICATION INTERNAL DATABASE (App DB)
# Used for: Users, Roles, Audit Logs, Dataset Metadata, Job Definitions
# Configured via: Environment variables ONLY
# Access: Backend services only, NEVER exposed to SQL Editor
# ============================================================================

# App DB Engine - Connects to AI_Data_Management
try:
    app_engine = create_engine(
        settings.DATABASE_URL,  # Directly from env, no dynamic config
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={'connect_timeout': 10}
    )
except Exception:
    # If initial connection fails, create engine anyway
    app_engine = create_engine(
        settings.DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={'connect_timeout': 10}
    )

AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)

Base = declarative_base()


def get_app_db() -> Generator[Session, None, None]:
    """Dependency for App DB session (internal operations)."""
    db = AppSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_app_db_context() -> Generator[Session, None, None]:
    """Context manager for App DB session."""
    db = AppSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# USER OPERATIONAL DATABASE (User DB)
# Used for: Data operations, SQL execution, analytics
# Configured via: Application Settings UI
# Access: SQL Editor, Data Operations UI
# ============================================================================

class UserDatabaseManager:
    """Manager for User Operational Database connections."""
    
    def __init__(self):
        self._active_connection = None
    
    def get_active_connection_profile(self, app_db: Session):
        """Get the active connection profile from App DB."""
        from app.models import ConnectionProfile
        profile = app_db.query(ConnectionProfile).filter(
            ConnectionProfile.is_active == True
        ).first()
        return profile
    
    def create_engine(self, connection_string: str, read_only: bool = False):
        """Create a SQLAlchemy engine for User DB."""
        connect_args = {'connect_timeout': 10}
        
        # Add read-only enforcement if needed
        if read_only:
            connect_args['options'] = '-c default_transaction_read_only=on'
        
        return create_engine(
            connection_string,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=settings.DEBUG,
            connect_args=connect_args
        )
    
    @contextmanager
    def get_connection(self, app_db: Session):
        """
        Get a connection to the User Operational Database.
        
        CRITICAL: This connection is ONLY for user data operations.
        It MUST NOT be used to access App DB tables.
        """
        from app.core.crypto import decrypt_value
        
        profile = self.get_active_connection_profile(app_db)
        
        if not profile:
            raise ValueError(
                "No active User Database connection configured. "
                "Please configure a connection in Settings → Data Connections."
            )
        
        # Decrypt password
        decrypted_password = decrypt_value(profile.encrypted_password) if profile.encrypted_password else ""
        
        # Generate connection string
        connection_string = profile.get_connection_string(decrypted_password)
        
        # Create ephemeral engine
        engine = self.create_engine(connection_string, profile.is_read_only)
        
        try:
            connection = engine.connect()
            yield connection
        finally:
            connection.close()
            engine.dispose()


# Global User DB Manager
user_db_manager = UserDatabaseManager()


def get_user_db(app_db: Session = None):
    """
    Dependency for User DB connection.
    
    SECURITY: This connection MUST ONLY be used for user data operations.
    It is isolated from the App DB and cannot access internal tables.
    """
    if app_db is None:
        raise ValueError("App DB session required to fetch User DB connection profile")
    
    with user_db_manager.get_connection(app_db) as conn:
        yield conn


# ============================================================================
# DUCKDB (Analytics Engine)
# Used for: In-memory analytics, data transformations
# ============================================================================

class DuckDBManager:
    """Manager for DuckDB analytics database."""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            os.makedirs(os.path.dirname(settings.DUCKDB_PATH), exist_ok=True)
            self._connection = duckdb.connect(settings.DUCKDB_PATH)
    
    @property
    def connection(self):
        return self._connection
    
    def execute(self, query: str, params: list = None):
        """Execute a query and return results."""
        if params:
            return self._connection.execute(query, params)
        return self._connection.execute(query)
    
    def query_df(self, query: str, params: list = None):
        """Execute query and return pandas DataFrame."""
        result = self.execute(query, params)
        return result.df()
    
    def register_dataframe(self, name: str, df):
        """Register a pandas DataFrame as a virtual table."""
        self._connection.register(name, df)
    
    def unregister(self, name: str):
        """Unregister a virtual table."""
        self._connection.unregister(name)
    
    def close(self):
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


def get_duckdb() -> DuckDBManager:
    """Get DuckDB manager instance."""
    return DuckDBManager()


# ============================================================================
# LEGACY COMPATIBILITY (DEPRECATED)
# ============================================================================

# Backward compatibility - these should be replaced with get_app_db
get_db = get_app_db
get_db_context = get_app_db_context
engine = app_engine
SessionLocal = AppSessionLocal

