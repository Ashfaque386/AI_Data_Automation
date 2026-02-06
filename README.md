# Enterprise Data Operations Platform

A production-grade, local-first data operations console combining the ease of Excel with the power of SQL and AI. Built for privacy, performance, and flexibility.

## 🌟 Key Features

### 🔐 Security & Access Control
- **Secure Authentication**: Built-in login system with JWT-based sessions.
- **Default Admin**: Pre-configured admin account for immediate access.
- **Role-Based Framework**: Full RBAC with user, role, and permission management.
- **Dual Database Architecture**: Strict separation between App DB and User DB for enhanced security.

### 📂 Unified Data Management
- **Multi-Format Ingestion**: Drag-and-drop upload for CSV, Excel, and JSON files.
- **Dedicated File Manager**: "Uploaded Files" view to manage raw assets.
- **Data Preview**: "Data Sources" view provides an interactive grid to inspect, sort, and filter data.

### ⚡ SQL Workspace
- **Integrated SQL Editor**: Write and execute queries against your User Operational Database.
- **High Performance**: Execute complex queries with full PostgreSQL/MySQL support.
- **Strict Isolation**: SQL queries execute only on User DB, never on App DB.

### ✏️ Advanced Data Editing
- **Excel-Style Interface**: Double-click to edit cells inline.
- **Computed Columns**: Create dynamic columns using Excel-like formulas.
- **Undo/Redo**: Full history tracking for safe experimentation.
- **Bulk Operations**: Sort, filter, rename, and delete columns with ease.

### 🤖 AI-Powered Intelligence
- **Local AI Integration**: Connects to **Ollama** running on your host machine.
- **Privacy First**: Your data never leaves your environment.
- **Dynamic Configuration**: Switch between AI models on the fly via Settings.

---

## 🏗️ Dual Database Architecture

This platform uses a **strict dual database architecture** for enhanced security and governance:

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR HOST MACHINE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────┐       │
│  │  App Internal DB    │      │  User Operational DB │       │
│  │  (AI_Data_Management)│      │  (Rent_Management)   │       │
│  │  Port: 5432         │      │  Port: 5432          │       │
│  │                     │      │                      │       │
│  │  • Users & Auth     │      │  • Your Data Tables  │       │
│  │  • Audit Logs       │      │  • SQL Query Targets │       │
│  │  • Dataset Metadata │      │  • Data Operations   │       │
│  │  • Job Definitions  │      │                      │       │
│  │  • Connection Profiles│    │                      │       │
│  └─────────────────────┘      └─────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

| Database | Purpose | Configuration |
|----------|---------|---------------|
| **App Internal DB** | System operations (users, auth, logs, metadata) | `.env` file only |
| **User Operational DB** | Data operations, SQL queries, analytics | Settings UI |

---

## 🚀 Quick Start Guide

### Prerequisites
1. **Docker Desktop** (running)
2. **PostgreSQL** (installed on host, port 5432)
3. **Ollama** (optional, for AI features)

### Setup & Run

1. **Configure Environment**:
   Edit `.env` and set your App Database credentials:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/AI_Data_Management
   ```

2. **Start the Application**:
   ```powershell
   docker-compose up -d --build
   ```

3. **Access the Console**:
   - Open: **http://localhost:5173**
   - Login with: `admin@example.com` / `admin123`

4. **Configure User Database** (Settings → Database Configuration):
   - Enter your User Operational DB credentials
   - Click "Test Connection" then "Save Configuration"

---

## 🔧 Configuration

### Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | App Internal DB connection | `postgresql://postgres:root@host.docker.internal:5432/AI_Data_Management` |
| `OLLAMA_URL` | Ollama AI server | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | Default AI model | `llama2` |
| `SECRET_KEY` | JWT signing key | Change in production! |
| `DEBUG` | Debug mode | `true` or `false` |

### User Operational Database

Configure via **Settings → Database Configuration** in the UI:
- **Host**: Database server address
- **Port**: Database port (default: 5432)
- **User/Password**: Database credentials
- **Database**: Select from available databases

---

## 🔄 Maintenance

### Restart Commands

```powershell
# Full restart with rebuild
docker-compose down && docker-compose up -d --build

# Restart backend only
docker-compose restart backend

# View logs
docker-compose logs backend --tail=50
docker-compose logs frontend --tail=50
```

### Reset Data

```powershell
# WARNING: Deletes all data volumes
docker-compose down -v
```

---

## 🏗️ Technical Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | React, TypeScript, TanStack Query, Vite |
| **Backend** | FastAPI (Python), SQLAlchemy |
| **App Database** | PostgreSQL (users, metadata, audit) |
| **User Database** | PostgreSQL/MySQL (configurable) |
| **Analytics** | DuckDB (in-memory) |
| **AI** | Ollama (local LLM) |

---

## 📁 Project Structure

```
AI_Data_Automation/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Auth, RBAC, crypto
│   │   ├── models/        # SQLAlchemy models
│   │   └── services/      # Business logic
│   └── requirements.txt
├── frontend/
│   └── src/
├── docker-compose.yml
├── .env                   # Configuration
└── README.md
```

---

## 🔐 Security Features

- **Encrypted Credentials**: User DB passwords encrypted at rest (Fernet)
- **Strict DB Isolation**: SQL Editor cannot access App DB tables
- **JWT Authentication**: Secure token-based sessions
- **Audit Logging**: All operations logged to App DB
- **RBAC**: Role-based permission system

