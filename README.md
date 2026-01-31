# Enterprise Data Operations Platform

A production-grade, local-first data operations console combining the ease of Excel with the power of SQL and AI. Built for privacy, performance, and flexibility.

## 🌟 Key Features

### 🔐 Security & Access Control
- **Secure Authentication**: Built-in login system with JWT-based sessions.
- **Default Admin**: Pre-configured admin account for immediate access.
- **Role-Based Framework**: Foundation includes user and role management (backend).

### 📂 Unified Data Management
- **Multi-Format Ingestion**: Drag-and-drop upload for:
    - **CSV Files**: Standard delimited data.
    - **Excel Workbooks**: Support for `.xlsx` and `.xls`.
    - **JSON**: Structured data arrays.
- **Dedicated File Manager**: "Uploaded Files" view to manage raw assets.
- **Data Preview**: "Data Sources" view provides an interactive grid to inspect, sort, and filter data instantly.

### ⚡ SQL Workspace
- **Integrated SQL Editor**: Write and execute queries directly against your data using DuckDB's powerful analytical engine.
- **High Performance**: Execute complex joins and aggregations on local files with in-memory speed.

### ✏️ Advanced Data Editing
- **Excel-Style Interface**: Double-click to edit cells inline.
- **Computed Columns**: Create dynamic columns using Excel-like formulas (e.g., `=SUM([Price], [Tax])`).
- **Undo/Redo**: Full history tracking for safe experimentation.
- **Bulk Operations**: Sort, filter, rename, and delete columns with ease.

### 🤖 AI-Powered Intelligence
- **Local AI Integration**: Connects to **Ollama** running on your host machine.
- **Privacy First**: Your data never leaves your environment.
- **Dynamic Configuration**: Switch between AI models (e.g., Llama 3, Mistral) on the fly via Settings.

### ⚙️ System Configuration
- **Dynamic Database Setup**: Configure your PostgreSQL metadata connection directly from the UI.
- **AI Model Selection**: Choose which local LLM to use for assistance without restarting the app.

---

## 🚀 Quick Start Guide

### Prerequisites
1.  **Docker Desktop** (running).
2.  **PostgreSQL 18** (installed on host, port 5432).
3.  **Ollama** (installed on host, port 11434, optional for AI).

### Setup & Run

1.  **Start the Application**:
    ```powershell
    docker-compose up --build
    ```
    *This builds the frontend and backend containers and starts the network.*

2.  **Access the Console**:
    -   Open your browser to: **[http://localhost:5173](http://localhost:5173)**
    -   You will be redirected to the login page.

3.  **Login**:
    -   **Email**: `admin@example.com`
    -   **Password**: `admin123`

---

## 🚦 Usage Workflow

Follow this standard workflow to get value immediately:

1.  **� Import Data**: 
    -   Navigate to **Uploaded Files** in the sidebar.
    -   Click the **Upload** area and select your file.
    -   *Result*: The file is ingested and a dataset is created automatically.

2.  **� Inspect Data**:
    -   Navigate to **Data Sources**.
    -   Click on any dataset in the sidebar.
    -   *Result*: View the data grid to verify contents, structure, and quality.

3.  **🧠 Analyze with SQL**:
    -   Navigate to **SQL Workspace**.
    -   Write SQL queries to join datasets or calculate metrics.
    -   *Example*: `SELECT category, SUM(amount) FROM "sales_data" GROUP BY category`

4.  **⚙️ Configure System**:
    -   Navigate to **Settings**.
    -   Update your AI Model or Database connection string if needed.

---

## 🔄 Maintenance & Restarting

There are several ways to restart the application depending on your needs.

### 1. Full System Restart
Use this when you want to completely stop and start fresh (e.g., after changing `.env` variables or port configurations).

```powershell
# Stop all services
docker-compose down

# Start all services (and rebuild if code changed)
docker-compose up -d --build
```

### 2. Restarting a Single Service
Use this if you only modified code in one part of the stack (e.g., Backend Python code) and want a quick reload.

```powershell
# Restart Backend only
docker-compose restart backend

# Restart Frontend only
docker-compose restart frontend
```

### 3. Resetting Data
**WARNING**: This will delete all docker volumes (uploaded files and metadata inside the container network).

```powershell
docker-compose down -v
```

---

## 🏗️ Technical Architecture

The platform runs as a coordinated set of Docker containers interacting with services on your host machine.

```
┌─────────────────────────────────────────┐
│  💻 YOUR HOST MACHINE                    │
│                                         │
│  ┌──────────────┐    ┌──────────────┐   │
│  │  PostgreSQL  │    │  Ollama (AI) │   │
│  │  Port: 5432  │    │  Port: 11434 │   │
│  └──────▲───────┘    └──────▲───────┘   │
│         │ (Metadata)        │ (LLM API) │
└─────────┼───────────────────┼───────────┘
          │                   │
┌─────────┴───────────────────┴───────────┐
│  🐳 DOCKER NETWORK                       │
│                                         │
│  ┌─────────────┐       ┌──────────────┐ │
│  │   Backend   │◀─────▶│   Frontend   │ │
│  │ (FastAPI)   │       │ (React/Vite) │ │
│  │  Port: 8000 │       │  Port: 5173  │ │
│  └─────────────┘       └──────────────┘ │
└─────────────────────────────────────────┘
```

-   **Frontend**: React, TypeScript, TanStack Query, Vite.
-   **Backend**: FastAPI (Python), DuckDB (Analytics), SQLAlchemy (ORM).
-   **Database**: PostgreSQL (User/Dataset Metadata).
-   **AI**: Ollama (Local LLM Inference).

## 🔧 Configuration

All configuration is managed via the UI or the `.env` file.

**Sample `.env`**:
```env
# Database Connection (Host)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/dataops

# AI Connection (Host)
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama2
AI_ENABLED=true
```
