# Windows Setup Notes

## PostgreSQL on Windows (Version 18)

### Finding PostgreSQL Installation

PostgreSQL 18 is typically installed in:
- `C:\Program Files\PostgreSQL\18\bin\`

### Option 1: Use Full Path

```powershell
# Check version
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version

# Connect to your EXISTING database
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d your_existing_db
```

### Option 2: Add to PATH (Recommended)

**Temporary (current session only):**
```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
```

**Permanent:**
1. Open System Properties → Environment Variables
2. Edit "Path" under System Variables
3. Add: `C:\Program Files\PostgreSQL\18\bin`
4. Restart PowerShell

Then use normally:
```powershell
psql --version
```

### Option 3: Use pgAdmin

1. Open pgAdmin
2. Connect to PostgreSQL server
3. Right-click "Databases" → Create → Database
4. Name: `dataops`

## Docker on Windows

### Install Docker Desktop

1. Download from: https://www.docker.com/products/docker-desktop
2. Install and restart
3. Ensure WSL 2 is enabled

### Verify Docker

```powershell
docker --version
docker-compose --version
```

## Common Windows Issues

### Issue: `psql` not recognized

**Solution:** Add PostgreSQL to PATH (see above)

### Issue: Docker can't connect to host PostgreSQL

**Solution:** Use `host.docker.internal` in connection string (already configured)

### Issue: Permission denied on volumes

**Solution:** Ensure Docker Desktop has access to the drive:
1. Docker Desktop → Settings → Resources → File Sharing
2. Add `D:\` drive

### Issue: Line endings (CRLF vs LF)

**Solution:** Git should handle this automatically. If issues occur:
```powershell
git config core.autocrlf true
```

## Quick Start for Windows

```powershell
# 1. Verify PostgreSQL 18 connection
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version

# 2. Configure environment
copy .env.docker .env

# Edit .env file:
# - Replace YOUR_PASSWORD with your PostgreSQL password
# - Update DATABASE_URL to point to your existing database
# Example: DATABASE_URL=postgresql://postgres:mypass@host.docker.internal:5432/my_existing_db

# 3. Start Docker containers
docker-compose up --build

# 4. Access application
# http://localhost:5173
```

## Useful Windows Commands

```powershell
# Check what's using a port
netstat -ano | findstr :8000

# Kill process by PID
taskkill /PID <pid> /F

# View Docker logs
docker-compose logs -f

# Restart Docker Desktop
Restart-Service docker
```
