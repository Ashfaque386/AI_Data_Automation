import sys
import os
import sys
import os
from unittest.mock import MagicMock
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import declarative_base

# Mock duckdb
sys.modules['duckdb'] = MagicMock()

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd()))

try:
    from app.database import AppSessionLocal
except ImportError as e:
    print(f"Failed to import AppSessionLocal: {e}")
    sys.exit(1)

Base = declarative_base()

class ConnectionProfile(Base):
    __tablename__ = "connection_profiles"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    db_type = Column(String)

def check_connections():
    db = AppSessionLocal()
    try:
        connections = db.query(ConnectionProfile).all()
        print(f"Found {len(connections)} connections:")
        for conn in connections:
            print(f"- ID: {conn.id}, Name: '{conn.name}', DB Type: {conn.db_type}")
    except Exception as e:
        print(f"Error checking connections: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from app.config import settings
    print(f"Database URL: {settings.DATABASE_URL}")
    check_connections()
