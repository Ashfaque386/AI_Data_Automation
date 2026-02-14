# Getting Started Guide

Welcome to the AI Data Automation Platform! This guide will help you get up and running in minutes.

## Prerequisites

Before you begin, ensure you have:
- ✅ Docker Desktop installed and running
- ✅ PostgreSQL installed on your host machine (for App Internal DB)
- ✅ (Optional) MongoDB for NoSQL support
- ✅ (Optional) Ollama for AI features

## Quick Start

### 1. Initial Setup

**Clone or navigate to the project**:
```powershell
cd AI_Data_Automation
```

**Configure environment variables**:

Create or edit `.env` file in the root directory:
```env
# App Internal Database (Required)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/AI_Data_Management

# Security (Required)
SECRET_KEY=your-secret-key-change-in-production
DEBUG=true

# AI Integration (Optional)
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama2
```

**Create the App Internal Database**:
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE AI_Data_Management;
```

### 2. Start the Application

```powershell
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs (optional)
docker-compose logs -f
```

### 3. Access the Application

Open your browser and navigate to:
- **Application**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

**Default Login Credentials**:
- Email: `admin@example.com`
- Password: `admin123`

> [!WARNING]
> Change the default admin password immediately after first login!

### 4. First-Time Configuration

After logging in, you'll need to configure your operational database.

**Navigate to Settings**:
1. Click the **⚙️ Settings** icon in the sidebar
2. Go to **Database Configuration**

**Configure Your Database**:
- **Host**: `host.docker.internal` (for databases on your host)
- **Port**: `5432` (PostgreSQL) or `3306` (MySQL)
- **Database**: Select your database from the dropdown
- **Username**: Your database username
- **Password**: Your database password

**Test and Save**:
1. Click **Test Connection**
2. If successful, click **Save Configuration**

---

## Your First Tasks

### Task 1: Create a Database Connection

Database connections allow you to manage multiple databases from one interface.

1. **Navigate to Database Connections**:
   - Click **🔌 Connections** in the sidebar

2. **Add New Connection**:
   - Click **+ Add Connection**
   - Fill in the details:
     - **Name**: Give it a descriptive name (e.g., "Production DB")
     - **Database Type**: PostgreSQL, MySQL, or MongoDB
     - **Host**: Database server address
     - **Port**: Database port
     - **Database**: Database name
     - **Credentials**: Username and password

3. **Test and Save**:
   - Click **Test Connection**
   - If successful, click **Save**

### Task 2: Execute Your First SQL Query

1. **Navigate to SQL Workspace**:
   - Click **📊 SQL Workspace** in the sidebar

2. **Write a Query**:
   ```sql
   SELECT * FROM your_table LIMIT 10;
   ```

3. **Execute**:
   - Click **▶ Run Query** or press `Ctrl+Enter`
   - View results in the data grid below

4. **Export Results** (optional):
   - Click **Export** button
   - Choose CSV or Excel format

### Task 3: Import Data from a File

1. **Navigate to Data Import**:
   - Click **📥 Import** in the sidebar

2. **Upload File**:
   - Drag and drop a CSV, Excel, or JSON file
   - Or click **Browse** to select a file

3. **Configure Import**:
   - **Target Table**: Select or create a table
   - **Column Mapping**: Auto-mapped or manual mapping
   - **Import Mode**: 
     - Insert (add new rows)
     - Upsert (update or insert)
     - Truncate & Insert (replace all data)

4. **Execute Import**:
   - Click **Execute Import**
   - Monitor progress
   - Review summary

### Task 4: Query MongoDB (if you have MongoDB)

1. **Create MongoDB Connection**:
   - Go to **Database Connections**
   - Add connection with type **MongoDB**
   - Enter connection details or MongoDB URI

2. **Open Query Interface**:
   - Click **🍃 Query** button on your MongoDB connection

3. **Execute a Query**:
   - Select a collection
   - Choose operation (Find, Aggregate, Count, Distinct)
   - Enter query parameters
   - Click **Example** for sample queries
   - Click **▶ Execute Query**

4. **View Results**:
   - Results displayed in JSON tree viewer
   - Expand/collapse nested documents
   - Copy or download results

---

## Common Operations

### Changing Your Password

1. Click your profile icon (top-right)
2. Select **Change Password**
3. Enter current and new password
4. Click **Update**

### Managing Users (Admin Only)

1. Navigate to **Settings** → **User Management**
2. Click **Add User** to create new users
3. Assign roles and permissions
4. Users receive login credentials

### Scheduling Jobs

1. Navigate to **⏰ Jobs** in the sidebar
2. Click **Create Job**
3. Configure:
   - Job name and description
   - Database connection
   - SQL query to execute
   - Schedule (cron expression or interval)
4. Save and enable the job

### Viewing Audit Logs

1. Navigate to **Settings** → **Audit Logs**
2. Filter by:
   - User
   - Action type
   - Date range
   - Connection
3. Export logs for compliance

---

## Troubleshooting

### Can't Connect to Database

**Check**:
- Database is running
- Host is `host.docker.internal` (not `localhost`)
- Port is correct
- Credentials are valid
- Firewall allows connection

**Test from container**:
```powershell
docker exec -it dataops_backend psql -h host.docker.internal -U postgres -d your_db
```

### Application Won't Start

**Check logs**:
```powershell
docker-compose logs backend
docker-compose logs frontend
```

**Common issues**:
- Port 8000 or 5173 already in use
- Database connection failed (check `DATABASE_URL` in `.env`)
- Docker Desktop not running

### Slow Query Performance

**Tips**:
- Add indexes to frequently queried columns
- Use `LIMIT` for large result sets
- Optimize complex joins
- Check database connection pool settings

---

## Next Steps

Now that you're set up, explore these features:

1. **[Database Connections Guide](features/database-connections.md)** - Advanced connection management
2. **[MongoDB Query Guide](features/mongodb-queries.md)** - Master MongoDB queries
3. **[Data Import Guide](features/data-import.md)** - Advanced import techniques
4. **[Security & Permissions](features/security-permissions.md)** - RBAC and access control

---

## Getting Help

- **Documentation**: Check the `docs/` folder
- **API Reference**: http://localhost:8000/docs
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
- **GitHub Issues**: Report bugs or request features

---

## Best Practices

✅ **Change default passwords** immediately  
✅ **Use strong passwords** for database connections  
✅ **Enable credential rotation** for production  
✅ **Review audit logs** regularly  
✅ **Backup your databases** before major operations  
✅ **Test queries** on non-production data first  
✅ **Use connection-level permissions** to restrict access  
✅ **Keep Docker images updated** for security patches  

---

**Congratulations!** You're now ready to use the AI Data Automation Platform. Happy querying! 🚀
