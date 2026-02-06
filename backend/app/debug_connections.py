#!/usr/bin/env python
"""Debug script to check active connection profiles."""
import sys
sys.stdout.reconfigure(line_buffering=True)

from app.database import AppSessionLocal
from app.models import ConnectionProfile

db = AppSessionLocal()
try:
    print("="*50, flush=True)
    print("CHECKING CONNECTION PROFILES", flush=True)
    print("="*50, flush=True)
    
    connections = db.query(ConnectionProfile).all()
    print(f"Total Connection Profiles: {len(connections)}", flush=True)
    
    for c in connections:
        print(f"  ID={c.id}, Name='{c.name}', Active={c.is_active}, DB='{c.database}'", flush=True)
    
    active = db.query(ConnectionProfile).filter(ConnectionProfile.is_active == True).first()
    
    print("="*50, flush=True)
    if active:
        print(f"ACTIVE PROFILE FOUND: {active.name}", flush=True)
        print(f"  Host: {active.host}", flush=True)
        print(f"  Port: {active.port}", flush=True)
        print(f"  Database: {active.database}", flush=True)
    else:
        print("NO ACTIVE PROFILE FOUND!", flush=True)
    print("="*50, flush=True)
    
finally:
    db.close()
