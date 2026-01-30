# Enterprise Data Operations Platform

Production-grade data operations console combining Excel-level manipulation, SQL querying, and AI-assisted automation.

## 🚀 Quick Start (Docker)

### Prerequisites
- **Docker Desktop** installed
- **PostgreSQL** running on host (port 5432)
- **Ollama** running on host (port 11434, optional for AI)

### Setup & Run

```powershell
# 1. Start Application
docker-compose up --build

# 2. Access Application
# Open http://localhost:5173
# You will be redirected to the Login page.

# 3. Login
# Default Credentials:
# Email: admin@example.com
# Password: admin123

# 4. Configure System
# After login, you will land on the Home Dashboard.
# - Database: Click "Settings" to configure your PostgreSQL connection.
# - AI: Select your preferred AI model from the "Settings" page.
```

**✨ New Features:**
- **Dynamic Setup**: Configure your database and AI models directly from the UI.
- **Login First**: Secure by default - authentication required immediately.

## 🔄 Application Maintenance

### Restarting the Application
To apply configuration changes or restart services:

```powershell
# 1. Stop all services
docker-compose down

# 2. Start services (and rebuild if code changed)
docker-compose up -d --build

# 3. Restart a specific service (e.g., backend)
docker-compose restart backend
```

### Resetting Data
To completely reset the application ( WARNING: Deletes all data):

```powershell
docker-compose down -v
```

## 📖 Documentation

- **[Docker Setup Guide](DOCKER_SETUP.md)** - Detailed Docker instructions and troubleshooting
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

## 🎯 Features

### Core Capabilities
- **Multi-format file upload**: Excel (multi-sheet), CSV, JSON, Parquet
- **SQL query execution**: DuckDB-powered analytics engine
- **Excel formulas**: 30+ compatible functions (SUM, VLOOKUP, IF, etc.)
- **Data export**: Excel, CSV, JSON, Parquet formats
- **AI assistance**: Natural language to SQL, formula suggestions, data quality checks
- **Enterprise security**: JWT auth, RBAC, audit logging, column-level permissions

### Tech Stack

**Backend**:
- FastAPI 0.109 + Python 3.11
- PostgreSQL (metadata) + DuckDB (analytics)
- SQLAlchemy 2.0 ORM
- Ollama integration (local LLM)

**Frontend**:
- React 18 + TypeScript 5
- Vite 5 build system
- TanStack Query + Zustand
- Enterprise dark theme UI

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Host Machine                     │
│  ┌──────────────┐    ┌──────────────┐  │
│  │  PostgreSQL  │    │   Ollama     │  │
│  │  :5432       │    │   :11434     │  │
│  └──────────────┘    └──────────────┘  │
│         ▲                    ▲          │
└─────────┼────────────────────┼──────────┘
          │                    │
┌─────────┴────────────────────┴──────────┐
│      Docker Containers                   │
│  ┌─────────────┐    ┌──────────────┐   │
│  │  Backend    │───▶│  Frontend    │   │
│  │  FastAPI    │    │  React+Vite  │   │
│  │  :8000      │    │  :5173       │   │
│  └─────────────┘    └──────────────┘   │
└──────────────────────────────────────────┘
```

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Auth, RBAC, Audit
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── main.py       # FastAPI app
│   └── scripts/
│       └── init_db.py    # Database initialization
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Page layouts
│       ├── services/     # API client
│       └── store/        # State management
├── docker-compose.yml    # Container orchestration
├── Dockerfile.backend    # Backend container
├── Dockerfile.frontend   # Frontend container
└── .env.docker          # Environment template
```

## 🔧 Configuration

Edit `.env` file:

```env
# PostgreSQL on host
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/dataops

# Ollama on host (optional)
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama2
AI_ENABLED=true

# Security
SECRET_KEY=your-secure-random-key-here
DEBUG=true
```

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart backend

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

## 🔐 Default Credentials

- **Email**: admin@example.com
- **Password**: admin123

⚠️ **Change immediately in production!**

## 🤖 AI Features

Requires Ollama running on host:

```bash
# Verify Ollama
curl http://localhost:11434/api/version

# Pull model
ollama pull llama2
```

AI capabilities:
- Natural language → SQL conversion
- Excel formula suggestions
- Data quality issue detection
- Column type classification

## 🚦 Usage

1. **Upload Data**: Click "Data Sources" → "+ Upload" → Select Excel/CSV file
2. **View Data**: Select dataset from sidebar to view in grid
3. **Run SQL**: Click "SQL Workspace" → Enter query → Ctrl+Enter
4. **Export**: Select dataset → Export to Excel/CSV/JSON

## 🔍 API Endpoints

Access interactive docs at `http://localhost:8000/docs`

- `/api/auth/*` - Authentication (login, register, refresh)
- `/api/datasets/*` - Dataset management and data grid
- `/api/sql/*` - SQL execution and query history
- `/api/export/*` - Data export (Excel, CSV, JSON, Parquet)
- `/api/ai/*` - AI-assisted operations
- `/api/users/*` - User and role management

## 🛠️ Troubleshooting

**Backend can't connect to PostgreSQL:**
```powershell
# Verify PostgreSQL 18 is running (Windows)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version

# Check connection to your database
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d your_db_name -c "SELECT 1"
```

**Frontend can't reach backend:**
```powershell
# Check backend health
curl http://localhost:8000/health
```

**Port conflicts:**
```powershell
# Stop containers
docker-compose down

# Check what's using ports
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# Or change ports in docker-compose.yml
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed troubleshooting.

## 📊 Data Persistence

Data persists in host directories:
- `./uploads/` - Uploaded files
- `./data/` - DuckDB analytics database

## 🚀 Production Deployment

1. Update `.env`:
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Configure production database
   - Set appropriate CORS origins

2. Add reverse proxy (Nginx/Traefik)
3. Enable HTTPS/SSL
4. Set resource limits in docker-compose.yml

## 📝 License

Enterprise Data Operations Platform - Internal Use

---

**Need help?** Check [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed instructions.

#### 1. Setup PostgreSQL Database
```bash
# Create database
createdb dataops

# Or via psql
psql -U postgres
CREATE DATABASE dataops;
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
copy app\.env.example app\.env
# Edit app\.env with your PostgreSQL credentials

# Run backend
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run frontend
npm run dev
```

#### 4. Access the Application
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Default Login**: admin@example.com / admin123

### Option 2: Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📁 Project Structure

```
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API routes
│   │   ├── core/        # Auth, RBAC, Audit
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   ├── config.py    # Configuration
│   │   ├── database.py  # DB connections
│   │   └── main.py      # FastAPI app
│   └── requirements.txt
├── frontend/            # React + TypeScript
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page layouts
│   │   ├── services/    # API client
│   │   ├── store/       # State management
│   │   └── App.tsx
│   └── package.json
└── docker-compose.yml
```

## 🎯 Features

### ✅ Implemented
- **Authentication & Authorization**: JWT-based auth with RBAC
- **File Ingestion**: Excel, CSV, JSON multi-format support
- **SQL Engine**: DuckDB-powered query execution
- **Formula Engine**: 30+ Excel-compatible functions
- **Data Export**: Excel, CSV, JSON, Parquet
- **AI Integration**: Ollama-based NL→SQL, formula suggestions
- **Audit Logging**: Complete operation tracking
- **Enterprise UI**: Dark theme admin console

### 📝 Key Capabilities
- Multi-sheet Excel upload with schema detection
- Real-time SQL query execution & optimization
- Column-level permissions
- Dataset versioning
- Query history & favorites
- Data quality suggestions (AI)

## 🔧 Configuration

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/dataops
SECRET_KEY=your-secret-key
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Frontend (environment)
```env
VITE_API_URL=http://localhost:8000
```

## 📚 API Documentation

Access Swagger UI at `http://localhost:8000/docs` for:
- Authentication endpoints
- Dataset management
- SQL execution
- AI-assisted operations
- Export functionality

## 🎨 Tech Stack

**Backend**:
- FastAPI 0.109
- SQLAlchemy 2.0
- DuckDB 0.9
- PostgreSQL
- Pydantic v2
- Ollama (AI)

**Frontend**:
- React 18
- TypeScript 5
- Vite 5
- TanStack Query
- Zustand
- Axios

## 🔐 Default Credentials

First time setup creates a default admin user:
- **Email**: admin@example.com
- **Password**: admin123

**⚠️ Change these credentials immediately in production!**

## 📊 Database Schema

The platform uses PostgreSQL for metadata and DuckDB for analytics:
- **Users, Roles, Permissions**: RBAC system
- **Datasets, Columns, Versions**: Data catalog
- **Audit Logs**: Complete operation history
- **Query History**: SQL query versioning

## 🤖 AI Features (Ollama Required)

Make sure Ollama is running locally:
```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# Pull llama2 model if needed
ollama pull llama2
```

AI features include:
- Natural language to SQL conversion
- Excel formula suggestions
- Data quality issue detection
- Column type classification

## 🐳 Production Deployment

1. Update `.env` with production values
2. Set `DEBUG=false`
3. Use strong `SECRET_KEY`
4. Configure PostgreSQL with production credentials
5. Set up SSL/TLS termination
6. Deploy via Docker Compose or Kubernetes

## 📖 Additional Documentation

For detailed information on specific components:
- See `implementation_plan.md` for architecture details
- Check `/docs` endpoint for API documentation
- Review code comments for implementation details
