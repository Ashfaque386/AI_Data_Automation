# Security & Permissions Guide

Complete guide to security features, RBAC, and access control in the AI Data Automation Platform.

## Overview

The platform provides enterprise-grade security with role-based access control (RBAC), connection-level permissions, schema restrictions, and credential management.

---

## Authentication

### User Login

**Default Admin**:
- Email: `admin@example.com`
- Password: `admin123`

> [!WARNING]
> Change the default admin password immediately!

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- Special characters recommended

### Session Management

- JWT-based authentication
- Tokens expire after 24 hours
- Automatic logout on expiration
- Refresh tokens for extended sessions

---

## Role-Based Access Control (RBAC)

### Built-in Roles

**Admin**:
- Full system access
- User management
- Role management
- All database operations

**User**:
- View and query databases
- Import data
- Create jobs
- No admin functions

**Read-Only**:
- View data only
- Execute SELECT queries
- No modifications

### Custom Roles

Create custom roles with specific permissions:

1. Navigate to **Settings** → **Roles**
2. Click **Create Role**
3. Enter role name and description
4. Select permissions
5. Save

### Permissions

**System Permissions**:
- `admin:manage` - Full admin access
- `users:manage` - User management
- `roles:manage` - Role management
- `audit:view` - View audit logs

**Data Permissions**:
- `data:read` - View and query data
- `data:write` - Insert, update, delete
- `data:import` - Import data
- `data:export` - Export data

**Connection Permissions**:
- `connections:manage` - Manage connections
- `connections:query` - Execute queries
- `connections:admin` - Full connection access

**Job Permissions**:
- `jobs:create` - Create jobs
- `jobs:execute` - Execute jobs
- `jobs:manage` - Manage all jobs

---

## Connection-Level Permissions

### Overview

Control access to specific database connections per user or role.

### Granting Access

1. Go to **Database Connections**
2. Click **Manage Permissions** on a connection
3. Click **Add User/Role**
4. Select user or role
5. Choose permission level:
   - **Read**: SELECT queries only
   - **Write**: Read + INSERT, UPDATE, DELETE
   - **Admin**: Full access including DDL
6. Save

### Permission Levels

**Read**:
- Execute SELECT queries
- View table structures
- Export data

**Write**:
- All Read permissions
- INSERT, UPDATE, DELETE
- Import data
- Execute stored procedures

**Admin**:
- All Write permissions
- CREATE, ALTER, DROP tables
- Manage indexes
- Grant permissions

### Revoking Access

1. Go to **Manage Permissions**
2. Find user/role
3. Click **Remove**
4. Confirm

---

## Schema Restrictions

### Overview

Limit access to specific schemas within a database connection.

### Setting Restrictions

1. Click **Manage Permissions** on connection
2. Select user/role
3. Click **Schema Restrictions**
4. Select allowed schemas:
   - `public` (PostgreSQL)
   - `dbo` (SQL Server)
   - Custom schemas
5. Save

### Behavior

**Allowed Schemas**:
- User can query tables in these schemas
- Can list tables and columns
- Can execute queries

**Restricted Schemas**:
- User cannot see tables
- Queries fail with permission error
- No access to data

### Example

```sql
-- User has access to 'sales' schema only

-- ✅ Allowed
SELECT * FROM sales.orders;

-- ❌ Denied
SELECT * FROM hr.employees;
```

---

## Table Restrictions

### Overview

Limit access to specific tables within allowed schemas.

### Setting Restrictions

1. In **Schema Restrictions** dialog
2. Select schema
3. Click **Table Restrictions**
4. Select allowed tables
5. Save

### Use Cases

- Restrict access to sensitive tables (e.g., `users`, `passwords`)
- Limit access to specific data sets
- Implement data segregation

---

## Credential Security

### Encryption

All database credentials are encrypted at rest using Fernet encryption.

**Features**:
- AES-128 encryption
- Unique encryption key per installation
- Keys stored securely in environment

### Credential Rotation

Regularly rotate database credentials for security.

**Steps**:
1. Click **Rotate Credential** on connection
2. Enter new password
3. Set rotation interval:
   - 30 days
   - 60 days
   - 90 days (recommended)
4. Click **Rotate**

**What Happens**:
- Old password replaced with new
- Credential metadata updated
- Expiration date set
- Audit log entry created

### Expiring Credentials

**Dashboard Widget**:
- Shows connections with expiring credentials
- Warning at 7 days before expiration
- Quick rotation access

**Email Notifications** (if configured):
- 7 days before expiration
- 1 day before expiration
- On expiration

### Credential Metadata

Each connection stores:
- Last rotation date
- Expiration date
- Rotation interval
- Encryption key version

---

## Audit Logging

### Overview

All operations are logged for compliance and security monitoring.

### Logged Events

**Authentication**:
- Login attempts (success/failure)
- Logout
- Password changes

**Database Operations**:
- Query execution
- Data modifications
- Schema changes
- Connection creation/modification

**Permission Changes**:
- Role assignments
- Permission grants/revokes
- Schema restrictions

**Credential Operations**:
- Credential rotations
- Password changes
- Connection updates

### Viewing Audit Logs

1. Navigate to **Settings** → **Audit Logs**
2. Filter by:
   - User
   - Action type
   - Date range
   - Connection
   - Status (success/failure)
3. Export logs for compliance

### Audit Log Details

Each log entry contains:
- Timestamp
- User ID and email
- Action type
- Resource (connection, table, etc.)
- Status (success/failure)
- IP address
- Additional metadata

---

## Best Practices

### User Management

✅ **Use least privilege** - Grant minimum required permissions  
✅ **Create role-based access** - Assign users to roles, not individual permissions  
✅ **Regular access reviews** - Review user permissions quarterly  
✅ **Disable inactive users** - Remove access for departed employees  
✅ **Use strong passwords** - Enforce password complexity  

### Connection Security

✅ **Use read-only credentials** for query-only users  
✅ **Rotate credentials** every 90 days  
✅ **Enable SSL/TLS** for production databases  
✅ **Limit schema access** to required schemas only  
✅ **Monitor connection usage** via audit logs  

### Credential Management

✅ **Never share passwords** - Each user has their own account  
✅ **Use environment variables** for sensitive config  
✅ **Rotate on schedule** - Don't wait for breach  
✅ **Monitor expiration** - Set up notifications  
✅ **Use strong passwords** - 16+ characters, random  

### Audit & Compliance

✅ **Review logs regularly** - Weekly or monthly  
✅ **Export logs** for long-term storage  
✅ **Monitor failed logins** - Detect brute force attempts  
✅ **Track permission changes** - Who granted what to whom  
✅ **Investigate anomalies** - Unusual query patterns  

---

## Security Checklist

### Initial Setup

- [ ] Change default admin password
- [ ] Create admin user with strong password
- [ ] Disable default admin account (optional)
- [ ] Configure SECRET_KEY in .env
- [ ] Enable SSL/TLS for databases

### User Management

- [ ] Create roles for different access levels
- [ ] Assign users to appropriate roles
- [ ] Set up connection-level permissions
- [ ] Configure schema restrictions
- [ ] Review and approve all access requests

### Credential Management

- [ ] Rotate all default passwords
- [ ] Set up credential rotation schedule
- [ ] Configure expiration notifications
- [ ] Document credential rotation process
- [ ] Store encryption keys securely

### Monitoring

- [ ] Enable audit logging
- [ ] Set up log review schedule
- [ ] Configure alerts for suspicious activity
- [ ] Export logs for compliance
- [ ] Monitor connection health

---

## Common Scenarios

### Scenario 1: New Employee

1. Create user account
2. Assign to appropriate role (e.g., "User")
3. Grant connection permissions as needed
4. Set schema restrictions if required
5. User receives login credentials

### Scenario 2: Employee Departure

1. Disable user account
2. Revoke all connection permissions
3. Review audit logs for their activity
4. Rotate credentials they had access to
5. Document in audit log

### Scenario 3: Contractor Access

1. Create limited user account
2. Grant read-only access
3. Set schema restrictions to specific schemas
4. Set expiration date for account
5. Monitor usage closely

### Scenario 4: Security Incident

1. Review audit logs for suspicious activity
2. Identify affected connections
3. Rotate all credentials immediately
4. Revoke compromised user access
5. Investigate and document incident

---

## Troubleshooting

### Permission Denied Errors

**Check**:
1. User has connection permission
2. Permission level is sufficient (Read/Write/Admin)
3. Schema is in allowed list
4. Table is in allowed list (if restricted)
5. Database user has required privileges

**Grant Database Permissions**:
```sql
-- PostgreSQL
GRANT SELECT ON ALL TABLES IN SCHEMA public TO user;

-- MySQL
GRANT SELECT ON database.* TO 'user'@'%';
```

### Cannot Rotate Credentials

**Check**:
- User has admin permission
- New password meets requirements
- Database is accessible
- Connection is active

### Audit Logs Not Showing

**Check**:
- Audit logging is enabled
- Database connection is active
- User has `audit:view` permission
- Date range filter is correct

---

## Compliance

### GDPR

- Audit logs track all data access
- User consent can be logged
- Data export capabilities
- Right to be forgotten (delete user data)

### SOC 2

- Access controls (RBAC)
- Audit logging
- Credential encryption
- Regular access reviews

### HIPAA

- Audit trails
- Access controls
- Encryption at rest
- Credential management

---

## Next Steps

- **[Database Connections](database-connections.md)** - Connection management
- **[Audit Logs](../getting-started.md#viewing-audit-logs)** - Monitoring access
- **[Troubleshooting](../troubleshooting.md#authentication-issues)** - Security issues

---

**Remember**: Security is everyone's responsibility! 🔒
