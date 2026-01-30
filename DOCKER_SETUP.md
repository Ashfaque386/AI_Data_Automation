# 🐳 Docker Setup Guide

Complete guide for running the Enterprise Data Operations Platform with Docker.

## Prerequisites

✅ **On Host Machine:**
- Docker Desktop installed and running
- PostgreSQL running (port 5432)
- Ollama running (port 11434, optional for AI)

## Quick Start

### 1. Verify Prerequisites

### 1. Verify Prerequisites

**PostgreSQL 18 (Windows):**

```powershell
# Verify version using full path (adjust path if installed elsewhere)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version

# Verify connection to your EXISTING database
# Replace 'your_db_name' with your actual database name
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d your_db_name -c "SELECT version();"
```

**Ollama (optional):**
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/version

# Pull model
ollama pull llama2
```

### 2. Configure Environment

```powershell
# Copy template
copy .env.docker .env

# Edit .env file and update:
```

**Edit `.env` with your settings:**
```env
# Use your existing database
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/YOUR_DATABASE_NAME

# Example:
# DATABASE_URL=postgresql://postgres:mypassword@host.docker.internal:5432/myexistingdb

OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama2
SECRET_KEY=your-secure-random-key
```

### 3. Start Application

```powershell
docker-compose up --build
```

**First run will:**
- Build backend and frontend containers
- Create necessary tables in your existing database
- Initialize with default admin user
- Start both services

### 4. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Login:**
- Email: `admin@example.com`
- Password: `admin123`

## Docker Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Rebuild After Code Changes
```bash
docker-compose up --build
```

### Restart a Service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Execute Commands in Container
```bash
# Backend shell
docker exec -it dataops_backend bash

# Run database migrations
docker exec -it dataops_backend python scripts/init_db.py
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Host Machine                     │
│                                          │
│  ┌──────────────┐    ┌──────────────┐  │
│  │  PostgreSQL  │    │   Ollama     │  │
│  │  :5432       │    │   :11434     │  │
│  └──────────────┘    └──────────────┘  │
│         ▲                    ▲          │
│         │                    │          │
│  ┌──────┴────────────────────┴───────┐ │
│  │      Docker Network               │ │
│  │                                   │ │
│  │  ┌─────────────┐  ┌────────────┐ │ │
│  │  │  Backend    │  │  Frontend  │ │ │
│  │  │  :8000      │  │  :5173     │ │ │
│  │  └─────────────┘  └────────────┘ │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Data Persistence

Data is stored in host directories:
- `./uploads/` - Uploaded files
- `./data/` - DuckDB database files

These directories are mounted as volumes, so data persists even when containers are stopped.

## Troubleshooting

### Backend can't connect to PostgreSQL

**Error:** `could not connect to server`

**Solution:**
1. Verify PostgreSQL is running: `psql -U postgres -c "SELECT 1;"`
2. Check `.env` has correct password
3. Ensure database exists: `psql -U postgres -l | grep dataops`
4. On Windows, `host.docker.internal` should work automatically

### Backend can't connect to Ollama

**Error:** `Connection refused` or `AI features disabled`

**Solution:**
1. Verify Ollama is running: `curl http://localhost:11434/api/version`
2. Pull the model: `ollama pull llama2`
3. Check Ollama is listening on all interfaces (not just localhost)

### Frontend can't reach backend

**Error:** Network errors in browser console

**Solution:**
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify CORS settings in `.env`
3. Clear browser cache

### Port already in use

**Error:** `port is already allocated`

**Solution:**
```bash
# Stop conflicting services
docker-compose down

# Or change ports in docker-compose.yml
```

### Database initialization fails

**Solution:**
```bash
# Manually initialize
docker exec -it dataops_backend python scripts/init_db.py
```

## Production Deployment

For production:

1. **Update `.env`:**
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Configure production database URL
   - Set appropriate CORS origins

2. **Use production builds:**
   - Build optimized frontend: `npm run build`
   - Use production WSGI server (Gunicorn)

3. **Add reverse proxy:**
   - Use Nginx or Traefik
   - Enable HTTPS/SSL
   - Configure proper security headers

4. **Resource limits:**
   Add to `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

## Monitoring

### Health Checks

Both containers have health checks:
```bash
docker ps
```

Look for "healthy" status.

### Resource Usage

```bash
docker stats
```

### Container Logs

```bash
# Real-time logs
docker-compose logs -f --tail=100

# Save logs to file
docker-compose logs > logs.txt
```

## Cleanup

### Remove containers and images
```bash
docker-compose down --rmi all
```

### Remove volumes (⚠️ deletes data)
```bash
docker-compose down -v
```

### Full cleanup
```bash
docker system prune -a
```

---

**Need help?** Check the main [README.md](README.md) or [QUICKSTART.md](QUICKSTART.md) for more information.
