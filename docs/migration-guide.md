# Migration Guide

Guide for migrating between versions and from other platforms.

## Version Migration

### Upgrading to Latest Version

**Before Upgrading**:
1. **Backup databases**:
   ```powershell
   # Backup App DB
   docker exec -it dataops_backend /app/pg_dump -h host.docker.internal -U postgres -d AI_Data_Management > app_db_backup.sql
   
   # Backup User DB (if applicable)
   docker exec -it dataops_backend /app/pg_dump -h host.docker.internal -U postgres -d your_db > user_db_backup.sql
   ```

2. **Export configuration**:
   - Export connection profiles
   - Export user list
   - Export job definitions
   - Save `.env` file

3. **Note current version**:
   ```powershell
   docker exec -it dataops_backend python -c "from app import __version__; print(__version__)"
   ```

**Upgrade Steps**:

1. **Pull latest code**:
   ```powershell
   git pull origin main
   ```

2. **Stop containers**:
   ```powershell
   docker-compose down
   ```

3. **Rebuild images**:
   ```powershell
   docker-compose build --no-cache
   ```

4. **Start containers**:
   ```powershell
   docker-compose up -d
   ```

5. **Run migrations** (automatic on startup):
   - Database schema migrations run automatically
   - Check logs for migration status:
   ```powershell
   docker-compose logs backend | grep "migration"
   ```

6. **Verify upgrade**:
   - Login to application
   - Test database connections
   - Execute test query
   - Check job schedules

**Rollback** (if needed):
```powershell
# Stop containers
docker-compose down

# Checkout previous version
git checkout v1.0.0

# Restore database
psql -U postgres -d AI_Data_Management < app_db_backup.sql

# Rebuild and start
docker-compose up -d --build
```

---

## Breaking Changes by Version

### v2.0.0 (MongoDB Support)

**New Features**:
- MongoDB connection support
- MongoDB query interface
- Enhanced credential management

**Breaking Changes**:
- None

**Migration Steps**:
- Standard upgrade process
- No manual intervention required

**New Dependencies**:
- `pymongo==4.6.1` (auto-installed)

### v1.5.0 (RBAC & Security)

**New Features**:
- Role-based access control
- Connection-level permissions
- Schema restrictions
- Credential rotation

**Breaking Changes**:
- Permission model changed
- All users need role assignment

**Migration Steps**:
1. Upgrade as normal
2. Assign roles to all users:
   - Admin users → "Admin" role
   - Regular users → "User" role
3. Review connection permissions
4. Set up schema restrictions (optional)

**Database Changes**:
- New tables: `roles`, `permissions`, `user_roles`
- New columns in `connection_profiles`

### v1.0.0 (Initial Release)

**Features**:
- Multi-database support (PostgreSQL, MySQL)
- SQL workspace
- Data import
- Job scheduling
- Basic authentication

---

## Platform Migration

### From Other Tools

#### Migrating from DBeaver

**Export Connections**:
1. In DBeaver: Database → Export Connections
2. Save as XML or CSV

**Import to Platform**:
1. Create connections manually in UI
2. Use same credentials
3. Test each connection

**Migrate Queries**:
- Copy SQL queries from DBeaver
- Save in SQL Workspace
- Create jobs for scheduled queries

#### Migrating from pgAdmin

**Export Connections**:
- Note connection details from pgAdmin
- Export server list (if available)

**Import to Platform**:
1. Create PostgreSQL connections
2. Use same host, port, database
3. Test connections

**Migrate Scripts**:
- Copy SQL scripts
- Execute in SQL Workspace
- Schedule as jobs if needed

#### Migrating from MySQL Workbench

**Export Connections**:
1. Server → Data Export
2. Export connection details

**Import to Platform**:
1. Create MySQL connections
2. Match connection parameters
3. Test connections

**Migrate Queries**:
- Copy saved queries
- Execute in SQL Workspace

---

## Data Migration

### Exporting Data

**From Old System**:
```sql
-- PostgreSQL
COPY table_name TO '/tmp/export.csv' CSV HEADER;

-- MySQL
SELECT * FROM table_name
INTO OUTFILE '/tmp/export.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n';
```

**From Application**:
1. Execute SELECT query
2. Click Export
3. Choose CSV or Excel
4. Save file

### Importing Data

**To New System**:
1. Navigate to Data Import
2. Upload exported file
3. Map columns
4. Choose import mode
5. Execute import

**Bulk Import** (large datasets):
```sql
-- PostgreSQL
COPY table_name FROM '/path/to/file.csv' CSV HEADER;

-- MySQL
LOAD DATA INFILE '/path/to/file.csv'
INTO TABLE table_name
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
```

---

## User Migration

### Exporting Users

**From Old System**:
```sql
SELECT email, name, role FROM users;
```

**Export to CSV**:
- Save user list
- Include roles and permissions

### Importing Users

**Manual Creation**:
1. Navigate to Settings → User Management
2. Create each user
3. Assign roles
4. Set connection permissions

**Bulk Creation** (via database):
```sql
-- Connect to App DB
INSERT INTO users (email, name, hashed_password, is_active)
VALUES ('user@example.com', 'User Name', 'hashed_password', true);

-- Assign role
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r
WHERE u.email = 'user@example.com' AND r.name = 'User';
```

---

## Configuration Migration

### Environment Variables

**Old `.env`**:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/old_db
SECRET_KEY=old_secret
```

**New `.env`**:
```env
DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/AI_Data_Management
SECRET_KEY=new_secret_change_this
OLLAMA_URL=http://host.docker.internal:11434
```

**Migration**:
1. Copy `.env` to `.env.backup`
2. Update `DATABASE_URL` to new App DB
3. Generate new `SECRET_KEY`
4. Add new variables as needed

### Connection Profiles

**Export** (via database):
```sql
SELECT name, db_type, host, port, database, username
FROM connection_profiles;
```

**Import**:
- Create connections via UI
- Or bulk insert into database

---

## Job Migration

### Exporting Jobs

**From Old System**:
- Export job definitions
- Note schedules and queries

**From Application**:
```sql
SELECT name, connection_id, query, schedule
FROM scheduled_jobs;
```

### Importing Jobs

**Via UI**:
1. Navigate to Jobs
2. Create each job
3. Set schedule
4. Test execution

**Via Database**:
```sql
INSERT INTO scheduled_jobs (name, connection_id, query, schedule, is_active)
VALUES ('Daily Report', 1, 'SELECT * FROM sales', '0 9 * * *', true);
```

---

## MongoDB Migration

### From MongoDB Compass

**Export Collections**:
1. In Compass: Collection → Export Collection
2. Save as JSON or CSV

**Import to Platform**:
1. Create MongoDB connection
2. Use `mongoimport` or MongoDB Query Interface
3. Insert documents

### From mongodump

**Export**:
```powershell
mongodump --uri="mongodb://localhost:27017/mydb" --out=./backup
```

**Import**:
```powershell
mongorestore --uri="mongodb://localhost:27017/mydb" ./backup
```

---

## Troubleshooting Migration

### Migration Fails

**Check**:
- Database is accessible
- Credentials are correct
- Sufficient disk space
- No conflicting data

**View Migration Logs**:
```powershell
docker-compose logs backend | grep "alembic"
```

### Data Loss

**Restore from Backup**:
```powershell
psql -U postgres -d AI_Data_Management < app_db_backup.sql
```

### Permission Issues

**After Migration**:
1. Verify user roles
2. Check connection permissions
3. Review schema restrictions
4. Test queries

---

## Post-Migration Checklist

- [ ] All users can login
- [ ] Database connections work
- [ ] Queries execute successfully
- [ ] Jobs are scheduled correctly
- [ ] Permissions are correct
- [ ] Audit logs are recording
- [ ] Backups are configured
- [ ] Documentation is updated

---

## Downgrade Procedure

**If upgrade fails**:

1. **Stop containers**:
   ```powershell
   docker-compose down
   ```

2. **Restore database**:
   ```powershell
   psql -U postgres -d AI_Data_Management < app_db_backup.sql
   ```

3. **Checkout previous version**:
   ```powershell
   git checkout v1.0.0
   ```

4. **Rebuild and start**:
   ```powershell
   docker-compose up -d --build
   ```

5. **Verify**:
   - Test login
   - Test connections
   - Test queries

---

## Getting Help

- **Documentation**: Check docs folder
- **Logs**: `docker-compose logs`
- **Backup**: Always backup before migration
- **Support**: Contact support team

---

**Remember**: Always backup before migrating! 💾
