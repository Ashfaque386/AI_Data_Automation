# Database Connections Guide

Complete guide to managing database connections in the AI Data Automation Platform.

## Overview

The platform supports multiple database connections, allowing you to manage PostgreSQL, MySQL, and MongoDB databases from a single interface.

---

## Creating Connections

### PostgreSQL Connection

1. Navigate to **Database Connections**
2. Click **+ Add Connection**
3. Fill in the details:
   - **Name**: `Production PostgreSQL`
   - **Database Type**: PostgreSQL
   - **Host**: `host.docker.internal` (or external host)
   - **Port**: `5432`
   - **Database**: `mydb`
   - **Username**: `postgres`
   - **Password**: Your password
4. Click **Test Connection**
5. If successful, click **Save**

### MySQL Connection

1. Navigate to **Database Connections**
2. Click **+ Add Connection**
3. Fill in the details:
   - **Name**: `MySQL Database`
   - **Database Type**: MySQL
   - **Host**: `host.docker.internal`
   - **Port**: `3306`
   - **Database**: `mydb`
   - **Username**: `root`
   - **Password**: Your password
4. Click **Test Connection**
5. If successful, click **Save**

### MongoDB Connection

**Standard Connection**:
1. Navigate to **Database Connections**
2. Click **+ Add Connection**
3. Fill in the details:
   - **Name**: `MongoDB Cluster`
   - **Database Type**: MongoDB
   - **Host**: `host.docker.internal`
   - **Port**: `27017`
   - **Database**: `mydb`
   - **Username**: (if auth enabled)
   - **Password**: (if auth enabled)
4. Click **Test Connection**
5. If successful, click **Save**

**MongoDB Atlas (URI)**:
1. Copy connection string from Atlas dashboard
2. Create connection with:
   - **Database**: Paste full URI
   - Example: `mongodb+srv://user:pass@cluster.mongodb.net/mydb`

---

## Managing Connections

### Viewing Connections

The Database Connections page shows all your connections with:
- **Name** and **Type**
- **Health Status** (Online/Offline/Degraded)
- **Last Used** timestamp
- **Action Buttons**

### Testing Connections

Click **Test** button to verify:
- Database is reachable
- Credentials are valid
- Connection is healthy

### Editing Connections

1. Click **Edit** button on a connection
2. Modify details as needed
3. Click **Test Connection** to verify changes
4. Click **Save**

### Deleting Connections

1. Click **Delete** button on a connection
2. Confirm deletion
3. Connection and associated permissions are removed

---

## Connection Features

### Health Monitoring

Connections show real-time health status:
- 🟢 **Online**: Connection is healthy
- 🔴 **Offline**: Cannot connect to database
- 🟡 **Degraded**: Connection is slow or unstable
- ⚪ **Unknown**: Status not yet checked

### Connection Pooling

The platform uses connection pooling for performance:
- **Pool Size**: Configurable per connection
- **Timeout**: Automatic timeout for idle connections
- **Retry Logic**: Automatic reconnection on failure

### SSL/TLS Support

Enable secure connections:
- **PostgreSQL**: SSL mode (require, verify-ca, verify-full)
- **MySQL**: SSL/TLS encryption
- **MongoDB**: TLS/SSL with certificate validation

---

## Permissions & Access Control

### Connection-Level Permissions

Control who can access each connection:

1. Click **Manage Permissions** on a connection
2. Add users or roles
3. Set permission level:
   - **Read**: View and query only
   - **Write**: Read + insert/update/delete
   - **Admin**: Full control including DDL

### Schema Restrictions

Limit access to specific schemas:

1. Click **Manage Permissions**
2. Select user/role
3. Click **Schema Restrictions**
4. Select allowed schemas
5. Save

### Table Restrictions

Limit access to specific tables:

1. In Schema Restrictions dialog
2. Select schema
3. Choose specific tables
4. Save

---

## Credential Management

### Credential Security

All credentials are encrypted at rest using Fernet encryption.

### Credential Rotation

Rotate credentials regularly for security:

1. Click **Rotate Credential** button
2. Enter new password
3. Set rotation interval (30/60/90 days)
4. Click **Rotate**

### Expiring Credentials

View connections with expiring credentials:
- Dashboard widget shows upcoming expirations
- Email notifications (if configured)
- Automatic reminders

---

## Advanced Features

### Connection Metadata

Each connection stores:
- Creation date and creator
- Last modified date
- Last used timestamp
- Health check history
- Query statistics

### Connection Tags

Organize connections with tags:
- Environment (dev, staging, prod)
- Department (sales, marketing, engineering)
- Region (us-east, eu-west)

### Connection Groups

Group related connections:
- Multi-database applications
- Microservices
- Regional databases

---

## Best Practices

### Naming Conventions

✅ **Use descriptive names**: `Production PostgreSQL - Orders DB`  
✅ **Include environment**: `Dev MySQL`, `Prod MongoDB`  
✅ **Include purpose**: `Analytics DB`, `Reporting DB`  
❌ **Avoid**: `DB1`, `Test`, `New Connection`

### Security

✅ **Use read-only credentials** for query-only users  
✅ **Rotate credentials** regularly (90 days)  
✅ **Enable SSL/TLS** for production databases  
✅ **Limit schema access** to required schemas only  
✅ **Review permissions** regularly  
✅ **Monitor audit logs** for suspicious activity

### Performance

✅ **Configure connection pools** appropriately  
✅ **Set reasonable timeouts** (30-60 seconds)  
✅ **Monitor connection health** regularly  
✅ **Close unused connections**  
✅ **Use indexes** on frequently queried tables

### Organization

✅ **Group by environment** (dev, staging, prod)  
✅ **Use consistent naming** across team  
✅ **Document connection purpose** in description  
✅ **Tag connections** for easy filtering  
✅ **Archive unused connections**

---

## Troubleshooting

### Connection Test Fails

**Check**:
- Database is running
- Host is correct (`host.docker.internal` for local)
- Port is correct
- Credentials are valid
- Firewall allows connection

**Test manually**:
```powershell
# PostgreSQL
psql -h host.docker.internal -U postgres -d mydb

# MySQL
mysql -h host.docker.internal -u root -p mydb

# MongoDB
mongosh mongodb://host.docker.internal:27017/mydb
```

### Connection Slow

**Solutions**:
- Increase connection pool size
- Reduce query timeout
- Check database server performance
- Optimize slow queries
- Add database indexes

### Permission Denied

**Check**:
- User has required permissions in database
- Connection-level permissions are set
- Schema restrictions allow access
- Table restrictions allow access

**Grant permissions**:
```sql
-- PostgreSQL
GRANT ALL PRIVILEGES ON DATABASE mydb TO myuser;
GRANT ALL PRIVILEGES ON SCHEMA public TO myuser;

-- MySQL
GRANT ALL PRIVILEGES ON mydb.* TO 'myuser'@'%';
FLUSH PRIVILEGES;
```

---

## Connection Examples

### Local Development

```yaml
Name: Dev PostgreSQL
Type: PostgreSQL
Host: host.docker.internal
Port: 5432
Database: dev_db
Username: postgres
Password: dev_password
```

### Production Database

```yaml
Name: Prod PostgreSQL
Type: PostgreSQL
Host: prod-db.example.com
Port: 5432
Database: prod_db
Username: app_user
Password: strong_password
SSL: Enabled (verify-full)
```

### MongoDB Atlas

```yaml
Name: Atlas Cluster
Type: MongoDB
Database: mongodb+srv://user:pass@cluster.mongodb.net/mydb?retryWrites=true&w=majority
```

### Read Replica

```yaml
Name: Read Replica
Type: PostgreSQL
Host: replica.example.com
Port: 5432
Database: prod_db
Username: readonly_user
Password: readonly_password
```

---

## Integration with Other Features

### SQL Workspace

- Select connection from dropdown
- Execute queries against selected connection
- Results cached per connection

### Data Import

- Import data to any connection
- Select target connection and table
- Supports all connection types

### Job Scheduling

- Schedule queries on specific connections
- Multi-connection jobs supported
- Connection health checked before execution

### Audit Logging

All connection operations are logged:
- Connection creation/modification/deletion
- Permission changes
- Credential rotations
- Query executions

---

## Next Steps

- **[MongoDB Query Guide](mongodb-queries.md)** - Query MongoDB databases
- **[Security & Permissions](security-permissions.md)** - Advanced RBAC
- **[Data Import Guide](data-import.md)** - Import data to connections

---

## Database-Specific Notes

### PostgreSQL

- Supports schemas and extensions
- Full DDL support
- Transaction support
- Advanced data types (JSON, arrays, etc.)

### MySQL

- Multiple storage engines (InnoDB, MyISAM)
- Full DDL support
- Transaction support (InnoDB)
- Stored procedures and triggers

### MongoDB

- NoSQL document database
- Collections instead of tables
- Flexible schema
- Aggregation framework
- No transactions (single document only)

---

**Remember**: Always test connections before saving and use strong, unique passwords! 🔒
