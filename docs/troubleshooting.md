# Troubleshooting Guide

Common issues and solutions for the AI Data Automation Platform.

## Table of Contents

- [Connection Issues](#connection-issues)
- [Query Problems](#query-problems)
- [Import Errors](#import-errors)
- [Performance Issues](#performance-issues)
- [Docker Problems](#docker-problems)
- [Authentication Issues](#authentication-issues)
- [MongoDB Specific](#mongodb-specific)

---

## Connection Issues

### Cannot Connect to Database

**Symptoms**: "Connection failed" error when testing database connection

**Solutions**:

1. **Check host address**:
   - ✅ Use `host.docker.internal` for databases on your host machine
   - ❌ Don't use `localhost` (won't work from Docker container)

2. **Verify database is running**:
   ```powershell
   # PostgreSQL
   psql -U postgres -l
   
   # MySQL
   mysql -u root -p -e "SHOW DATABASES;"
   
   # MongoDB
   mongosh --eval "db.adminCommand('ping')"
   ```

3. **Check port**:
   - PostgreSQL: 5432
   - MySQL: 3306
   - MongoDB: 27017

4. **Test from container**:
   ```powershell
   # PostgreSQL
   docker exec -it dataops_backend psql -h host.docker.internal -U postgres
   
   # MongoDB
   docker exec -it dataops_backend python -c "from pymongo import MongoClient; print(MongoClient('mongodb://host.docker.internal:27017').server_info())"
   ```

5. **Check firewall**:
   - Ensure database port is not blocked
   - Allow Docker network access

### Connection Timeout

**Symptoms**: Connection takes too long and times out

**Solutions**:

1. **Increase timeout** in connection settings
2. **Check network latency** to database server
3. **Verify database server** is not overloaded
4. **Check connection pool** settings

### Authentication Failed

**Symptoms**: "Authentication failed" or "Access denied"

**Solutions**:

1. **Verify credentials**:
   - Username is correct
   - Password is correct (no extra spaces)
   - User has access to the database

2. **Check user permissions**:
   ```sql
   -- PostgreSQL
   GRANT ALL PRIVILEGES ON DATABASE your_db TO your_user;
   
   -- MySQL
   GRANT ALL PRIVILEGES ON your_db.* TO 'your_user'@'%';
   FLUSH PRIVILEGES;
   ```

3. **MongoDB authentication**:
   - Verify authentication database (usually `admin`)
   - Check user roles

---

## Query Problems

### Query Returns No Results

**Symptoms**: Query executes but returns 0 rows

**Solutions**:

1. **Verify data exists**:
   ```sql
   SELECT COUNT(*) FROM your_table;
   ```

2. **Check filter conditions**:
   - Are column names correct? (case-sensitive)
   - Are values correct?
   - Remove filters one by one to isolate issue

3. **Check database/schema**:
   - Ensure you're querying the correct database
   - Verify schema name if using schema-qualified names

### Query Execution Error

**Symptoms**: "Syntax error" or "Column not found"

**Solutions**:

1. **Check SQL syntax**:
   - Missing commas, parentheses, or quotes
   - Reserved keywords (use quotes if needed)

2. **Verify column names**:
   ```sql
   -- PostgreSQL/MySQL
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'your_table';
   ```

3. **Check data types**:
   - String values need quotes: `'value'`
   - Numbers don't need quotes: `123`

### Query Too Slow

**Symptoms**: Query takes minutes to execute

**Solutions**:

1. **Add LIMIT**:
   ```sql
   SELECT * FROM large_table LIMIT 100;
   ```

2. **Check indexes**:
   ```sql
   -- PostgreSQL
   SELECT * FROM pg_indexes WHERE tablename = 'your_table';
   
   -- MySQL
   SHOW INDEX FROM your_table;
   ```

3. **Optimize query**:
   - Avoid `SELECT *`, specify columns
   - Use WHERE clause to filter early
   - Check EXPLAIN plan

4. **Add indexes**:
   ```sql
   CREATE INDEX idx_column ON your_table(column_name);
   ```

---

## Import Errors

### Import Failed

**Symptoms**: "Import failed" error during data import

**Solutions**:

1. **Check file format**:
   - CSV: Ensure proper delimiters
   - Excel: Verify file is not corrupted
   - JSON: Validate JSON syntax

2. **Check column mapping**:
   - All required columns are mapped
   - Data types match target table

3. **Check data types**:
   - Dates in correct format
   - Numbers don't contain text
   - NULL values handled correctly

4. **Check constraints**:
   - Primary key violations
   - Foreign key violations
   - Unique constraints
   - NOT NULL constraints

### Partial Import

**Symptoms**: Some rows imported, others failed

**Solutions**:

1. **Review error log**:
   - Check which rows failed
   - Identify common pattern

2. **Fix data issues**:
   - Remove invalid characters
   - Fix date formats
   - Handle NULL values

3. **Use batch mode**:
   - Import in smaller batches
   - Easier to identify problematic rows

### File Upload Failed

**Symptoms**: Cannot upload file

**Solutions**:

1. **Check file size**:
   - Maximum file size may be limited
   - Try compressing large files

2. **Check file permissions**:
   - Ensure file is not locked
   - Close file in Excel/other programs

3. **Check disk space**:
   ```powershell
   docker exec -it dataops_backend df -h
   ```

---

## Performance Issues

### Application Slow

**Symptoms**: UI is slow or unresponsive

**Solutions**:

1. **Check Docker resources**:
   - Increase memory allocation in Docker Desktop
   - Increase CPU allocation

2. **Check database performance**:
   - Run `VACUUM` (PostgreSQL)
   - Optimize tables (MySQL)
   - Check slow query log

3. **Clear browser cache**:
   - Hard refresh: `Ctrl+Shift+R`
   - Clear cookies and cache

### Large Result Sets

**Symptoms**: Browser freezes with large result sets

**Solutions**:

1. **Use LIMIT**:
   ```sql
   SELECT * FROM large_table LIMIT 1000;
   ```

2. **Export instead of viewing**:
   - Export to CSV/Excel
   - Open in external tool

3. **Use pagination**:
   - Query in batches
   - Use OFFSET and LIMIT

---

## Docker Problems

### Container Won't Start

**Symptoms**: `docker-compose up` fails

**Solutions**:

1. **Check logs**:
   ```powershell
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. **Check ports**:
   ```powershell
   # Check if ports are in use
   netstat -ano | findstr :8000
   netstat -ano | findstr :5173
   ```

3. **Remove old containers**:
   ```powershell
   docker-compose down
   docker-compose up -d --build
   ```

4. **Check Docker Desktop**:
   - Ensure Docker Desktop is running
   - Check for updates

### Database Migration Failed

**Symptoms**: "Migration failed" in logs

**Solutions**:

1. **Check DATABASE_URL** in `.env`:
   ```env
   DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/dbname
   ```

2. **Manually run migrations**:
   ```powershell
   docker exec -it dataops_backend alembic upgrade head
   ```

3. **Reset database** (WARNING: deletes all data):
   ```powershell
   docker-compose down -v
   docker-compose up -d --build
   ```

### Volume Permission Issues

**Symptoms**: "Permission denied" errors

**Solutions** (Linux/Mac):
```bash
sudo chown -R $USER:$USER ./uploads ./data ./backups
```

---

## Authentication Issues

### Cannot Login

**Symptoms**: "Invalid credentials" error

**Solutions**:

1. **Use default credentials**:
   - Email: `admin@example.com`
   - Password: `admin123`

2. **Reset password**:
   ```powershell
   docker exec -it dataops_backend python -c "
   from app.core.database import get_db
   from app.models.user import User
   from app.core.security import get_password_hash
   db = next(get_db())
   user = db.query(User).filter(User.email == 'admin@example.com').first()
   user.hashed_password = get_password_hash('newpassword')
   db.commit()
   "
   ```

3. **Check database**:
   - Ensure users table exists
   - Verify admin user exists

### Session Expired

**Symptoms**: Logged out unexpectedly

**Solutions**:

1. **Login again**
2. **Check SECRET_KEY** in `.env` (don't change in production)
3. **Clear browser cookies**

---

## MongoDB Specific

### MongoDB Connection Failed

**Symptoms**: Cannot connect to MongoDB

**Solutions**:

1. **Check MongoDB is running**:
   ```powershell
   mongosh --eval "db.adminCommand('ping')"
   ```

2. **Check connection string**:
   - Standard: `mongodb://host.docker.internal:27017`
   - Atlas: `mongodb+srv://user:pass@cluster.mongodb.net/db`

3. **Check authentication**:
   - Verify username and password
   - Check authentication database

4. **Install pymongo** (if missing):
   ```powershell
   docker exec -it dataops_backend pip install pymongo==4.6.1
   ```

### MongoDB Query Error

**Symptoms**: Query fails with error

**Solutions**:

1. **Validate JSON**:
   - Use JSON validator
   - Check for missing commas/brackets

2. **Check collection name**:
   - Case-sensitive
   - Verify collection exists

3. **Check field names**:
   - Case-sensitive
   - Use dot notation for nested fields: `"address.city"`

### MongoDB Aggregation Error

**Symptoms**: Aggregation pipeline fails

**Solutions**:

1. **Test stages individually**:
   - Run each stage separately
   - Identify problematic stage

2. **Check operator syntax**:
   - `$match`, `$group`, `$sort` are correct
   - Operators start with `$`

3. **Verify field references**:
   - Field references need `$`: `"$fieldName"`
   - Literal values don't need `$`

---

## Getting More Help

### Enable Debug Mode

Edit `.env`:
```env
DEBUG=true
```

Restart:
```powershell
docker-compose restart backend
```

### View Detailed Logs

```powershell
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Check Health Status

Visit: http://localhost:8000/health

### Export Logs

```powershell
docker-compose logs backend > backend.log
docker-compose logs frontend > frontend.log
```

### Database Logs

```sql
-- PostgreSQL slow queries
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- MySQL slow queries
SHOW FULL PROCESSLIST;
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Database not running | Start database service |
| `Authentication failed` | Wrong credentials | Verify username/password |
| `Table does not exist` | Wrong database/schema | Check database selection |
| `Syntax error` | Invalid SQL | Check SQL syntax |
| `Permission denied` | Insufficient privileges | Grant user permissions |
| `Timeout` | Query too slow | Add indexes, use LIMIT |
| `Invalid JSON` | Malformed JSON | Validate JSON syntax |
| `Port already in use` | Port conflict | Stop other service or change port |

---

## Still Need Help?

1. Check [Getting Started Guide](getting-started.md)
2. Review [Feature Guides](features/)
3. Check [API Documentation](http://localhost:8000/docs)
4. Search GitHub Issues
5. Contact support team

---

**Remember**: Most issues can be resolved by checking logs and verifying configuration! 🔍
