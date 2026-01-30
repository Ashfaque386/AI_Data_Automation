"""
Database Initialization Script
Creates default admin user and sets up RBAC
"""
import sys
import os
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models import User, Role
from app.core.rbac import initialize_rbac


def init_database():
    """Initialize database with tables and default data."""
    print("🔧 Checking database connection...")
    print(f"DEBUG: Engine URL: {engine.url}")
    
    try:
        # Test connection first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"⚠️  Database not configured yet: {str(e)}")
        print("ℹ️  Please configure database via the Setup UI at http://localhost:5173")
        return  # Exit gracefully without failing
    
    try:
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created")
        
        # Initialize RBAC
        db = SessionLocal()
        try:
            print("Setting up RBAC (roles and permissions)...")
            initialize_rbac(db)
            print("✓ RBAC initialized")
            
            # Check if admin user exists
            admin = db.query(User).filter(User.email == "admin@example.com").first()
            
            if not admin:
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
                print("✓ Admin user created")
                print("\n📧 Email: admin@example.com")
                print("🔑 Password: admin123")
                print("\n⚠️  IMPORTANT: Change this password immediately in production!")
            else:
                print("✓ Admin user already exists")
            
            print("\n✅ Database initialization complete!")
            
        except Exception as e:
            print(f"\n❌ Error during initialization: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        print(f"\n❌ Database initialization failed: {str(e)}")
        print("ℹ️  The application will start anyway. Configure via Setup UI.")
        return  # Don't crash, let the app start


if __name__ == "__main__":
    from sqlalchemy import text
    init_database()
