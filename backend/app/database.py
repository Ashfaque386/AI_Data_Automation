"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import duckdb
import os

from app.config import settings

# PostgreSQL Engine (for metadata, users, audit)
# Initial load uses settings, but can be reconfigured
# pool_pre_ping ensures connections are validated before use
try:
    engine = create_engine(
        settings.get_db_url(),
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={'connect_timeout': 10}
    )
except Exception:
    # If initial connection fails, create engine anyway
    # It will be reconfigured later via setup UI
    engine = create_engine(
        settings.get_db_url(),
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={'connect_timeout': 10}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reconfigure_engine():
    """Reconfigure database engine (e.g., after setup)."""
    global engine, SessionLocal
    if engine:
        engine.dispose()
    
    engine = create_engine(
        settings.get_db_url(),
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={'connect_timeout': 10}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
