from app.database import AppSessionLocal
from app.models import ConnectionProfile, User

db = AppSessionLocal()
try:
    user = db.query(User).first()
    print(f"User found: {user.email if user else 'None'}")
    
    connections = db.query(ConnectionProfile).all()
    print(f"Connection Profiles count: {len(connections)}")
    for c in connections:
        print(f" - ID: {c.id}, Name: {c.name}, Active: {c.is_active}, DB: {c.database}")
    
    active = db.query(ConnectionProfile).filter(ConnectionProfile.is_active == True).first()
    print(f"\nActive profile: {active.name if active else 'NONE FOUND'}")
finally:
    db.close()
