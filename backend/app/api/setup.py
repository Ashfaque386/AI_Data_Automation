"""
Setup API for initial configuration
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import structlog
from app.config import settings
from app.database import reconfigure_engine, Base
from app.core.rbac import initialize_rbac
from app.database import get_db_context

router = APIRouter()
logger = structlog.get_logger()


class ConnectionTestRequest(BaseModel):
    host: str
    port: int
    user: str
    password: str


class ConfigureRequest(ConnectionTestRequest):
    database: str


@router.post("/test-connection")
async def test_connection(request: ConnectionTestRequest):
    """Test connection to PostgreSQL and list databases."""
    url = f"postgresql://{request.user}:{request.password}@{request.host}:{request.port}/postgres"
    
    try:
        # Create temp engine to list DBs
        temp_engine = create_engine(url, connect_args={'connect_timeout': 5})
        with temp_engine.connect() as conn:
            # List only user databases, excluding templates
            result = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false;"))
            databases = [row[0] for row in result]
            
        return {
            "success": True,
            "databases": databases
        }
    except Exception as e:
        logger.error("connection_test_failed", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/configure")
async def configure_database(request: ConfigureRequest):
    """Save configuration and initialize database."""
    url = f"postgresql://{request.user}:{request.password}@{request.host}:{request.port}/{request.database}"
    
    try:
        # 1. Verify connection to specific DB
        temp_engine = create_engine(url, connect_args={'connect_timeout': 5})
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 2. Save config
        settings.save_db_config(url)
        
        # 3. Reconfigure global engine
        reconfigure_engine()
        
        # 4. Initialize schema and RBAC
        # Note: We need to import models here or in main to ensure they are registered
        from app.database import engine
        Base.metadata.create_all(bind=engine)
        
        with get_db_context() as db:
            initialize_rbac(db)
            
        return {"success": True, "message": "Database configured successfully"}
        
    except Exception as e:
        logger.error("configuration_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_status():
    """Check if database is configured."""
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"configured": True}
    except Exception:
        return {"configured": False}


@router.post("/create-admin")
async def create_admin_user():
    """Manually create default admin user if missing."""
    try:
        from app.models import User, Role
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Check if admin user exists
            admin = db.query(User).filter(User.email == "admin@example.com").first()
            if admin:
                return {"success": True, "message": "Admin user already exists"}
            
            # Create admin
            print("Creating default admin user...")
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            
            admin = User(
                email="admin@example.com",
                username="admin",
                full_name="System Administrator",
                hashed_password=User.hash_password("admin123"),
                is_superuser=True,
                is_active=True
            )
            
            if admin_role:
                admin.roles = [admin_role]
            
            db.add(admin)
            db.commit()
            return {"success": True, "message": "Admin user created successfully"}
        finally:
            db.close()
            
    except Exception as e:
        logger.error("admin_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
