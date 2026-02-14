# Data Import Guide

Complete guide to importing data from CSV, Excel, and JSON files into your databases.

## Overview

The Data Import feature allows you to quickly load data from files into your database tables with intelligent column mapping and validation.

---

## Supported File Formats

- **CSV** - Comma-separated values
- **Excel** - .xlsx and .xls files
- **JSON** - JSON arrays or newline-delimited JSON

---

## Import Process

### Step 1: Upload File

1. Navigate to **📥 Import** in the sidebar
2. **Drag and drop** a file or click **Browse**
3. File is uploaded and parsed
4. Preview shows first 10 rows

### Step 2: Select Target

1. **Select Database Connection**
2. **Select Target Table**:
   - Choose existing table
   - Or create new table

### Step 3: Map Columns

**Auto-Mapping**:
- Columns are auto-mapped by name similarity
- Review and adjust mappings

**Manual Mapping**:
- Click column dropdown to change mapping
- Select "Skip" to ignore a column
- Unmapped columns shown in red

**Data Type Detection**:
- System detects data types automatically
- Override if needed

### Step 4: Configure Import

**Import Mode**:
- **Insert**: Add new rows (fails on duplicates)
- **Upsert**: Update existing or insert new
- **Truncate & Insert**: Delete all data, then insert

**Options**:
- **Skip header row**: For CSV files with headers
- **Batch size**: Number of rows per batch (default: 1000)
- **On error**: Stop or continue on error

### Step 5: Execute Import

1. Click **Execute Import**
2. Monitor progress bar
3. Review summary:
   - Rows processed
   - Rows inserted/updated
   - Errors (if any)

---

## Import Modes

### Insert Mode

Adds new rows to the table.

**Use When**:
- Adding new data
- Table is empty
- No duplicate keys

**Behavior**:
- Fails if primary key/unique constraint violated
- All rows rolled back on error (transactional)

**Example**:
```
Before: 100 rows
Import: 50 rows
After: 150 rows
```

### Upsert Mode

Updates existing rows or inserts new ones.

**Use When**:
- Updating existing data
- Merging data
- Handling duplicates

**Requires**:
- Primary key or unique constraint

**Behavior**:
- Updates row if key exists
- Inserts row if key doesn't exist

**Example**:
```
Before: 100 rows (IDs 1-100)
Import: 50 rows (IDs 90-140)
After: 140 rows (IDs 1-140, rows 90-100 updated)
```

### Truncate & Insert

Deletes all data, then inserts new data.

**Use When**:
- Replacing all data
- Fresh data load
- No need to preserve existing data

**Behavior**:
- Deletes all rows from table
- Inserts new rows
- Resets auto-increment (if applicable)

**Example**:
```
Before: 100 rows
Import: 50 rows
After: 50 rows (all new)
```

---

## Column Mapping

### Auto-Mapping

System matches columns by:
1. **Exact name match** (case-insensitive)
2. **Similar names** (fuzzy matching)
3. **Position** (if names don't match)

### Manual Mapping

Click column dropdown to:
- Select different target column
- Skip column (don't import)
- Create new column

### Data Type Conversion

**Automatic Conversions**:
- String → Integer (if numeric)
- String → Date (if date format)
- Integer → String (always safe)

**Manual Override**:
- Click data type to change
- Validation errors shown in red

---

## Error Handling

### Validation Errors

**Common Errors**:
- Data type mismatch
- NULL in NOT NULL column
- Duplicate primary key
- Foreign key violation
- Value too long for column

**Resolution**:
1. Review error message
2. Fix data in source file
3. Re-upload and import

### Partial Imports

**On Error Behavior**:
- **Stop**: Rollback all changes
- **Continue**: Skip error rows, import rest

**Error Log**:
- Download error report
- Shows row number and error message
- Fix and re-import failed rows

---

## Best Practices

### Performance

✅ **Use batch imports** for large files (>10K rows)  
✅ **Disable indexes** before large imports  
✅ **Import during off-peak** hours  
✅ **Use CSV** for fastest imports  
✅ **Split large files** into smaller chunks  

### Data Quality

✅ **Validate data** before import  
✅ **Remove duplicates** in source file  
✅ **Use consistent date formats** (YYYY-MM-DD)  
✅ **Trim whitespace** from text fields  
✅ **Handle NULL values** explicitly  

### Safety

✅ **Backup table** before truncate & insert  
✅ **Test on small sample** first  
✅ **Use transactions** (automatic in Insert mode)  
✅ **Review mappings** carefully  
✅ **Check row counts** after import  

---

## File Format Guidelines

### CSV Files

**Best Practices**:
```csv
name,email,age,created_date
John Doe,john@example.com,30,2024-01-15
Jane Smith,jane@example.com,25,2024-01-16
```

**Tips**:
- Use comma as delimiter
- Quote fields with commas: `"Smith, John"`
- Use UTF-8 encoding
- Include header row
- Use consistent date format

### Excel Files

**Best Practices**:
- Use first row for headers
- One sheet per import
- Remove formulas (values only)
- No merged cells
- No empty rows/columns

**Supported**:
- .xlsx (Excel 2007+)
- .xls (Excel 97-2003)

### JSON Files

**Array Format**:
```json
[
  {"name": "John Doe", "email": "john@example.com", "age": 30},
  {"name": "Jane Smith", "email": "jane@example.com", "age": 25}
]
```

**Newline-Delimited**:
```json
{"name": "John Doe", "email": "john@example.com", "age": 30}
{"name": "Jane Smith", "email": "jane@example.com", "age": 25}
```

---

## Advanced Features

### Creating Tables

Import can create new tables:
1. Select "Create New Table"
2. Enter table name
3. System infers schema from data
4. Review and adjust column types
5. Set primary key (optional)

### Data Transformation

**During Import**:
- Trim whitespace
- Convert case (upper/lower)
- Replace values
- Parse dates

**After Import**:
- Use SQL to transform
- Create computed columns
- Normalize data

### Large File Imports

**For files >100MB**:
1. Split into smaller files
2. Import in batches
3. Monitor memory usage
4. Use database COPY command (advanced)

---

## Troubleshooting

### Import Fails Immediately

**Check**:
- File format is supported
- File is not corrupted
- File size is reasonable (<500MB)
- Database connection is active

### Slow Import

**Solutions**:
- Reduce batch size
- Disable indexes temporarily
- Import during off-peak hours
- Use CSV instead of Excel

### Data Type Errors

**Common Issues**:
```
Error: "123abc" cannot be converted to integer
Solution: Clean data or change column type to text

Error: "13/01/2024" is not a valid date
Solution: Use YYYY-MM-DD format

Error: Value too long for column (max 50 characters)
Solution: Increase column size or truncate data
```

### Foreign Key Violations

**Solution**:
1. Import parent table first
2. Then import child table
3. Or disable foreign key checks (advanced)

---

## Examples

### Example 1: Import Users from CSV

**File**: users.csv
```csv
name,email,age,country
John Doe,john@example.com,30,US
Jane Smith,jane@example.com,25,UK
```

**Steps**:
1. Upload users.csv
2. Select connection and table
3. Map columns (auto-mapped)
4. Choose Insert mode
5. Execute import
6. Result: 2 rows inserted

### Example 2: Update Products from Excel

**File**: products.xlsx
```
| product_id | name      | price |
|------------|-----------|-------|
| 1          | Widget A  | 19.99 |
| 2          | Widget B  | 29.99 |
```

**Steps**:
1. Upload products.xlsx
2. Select connection and products table
3. Map columns
4. Choose Upsert mode (updates existing)
5. Execute import
6. Result: 2 rows updated

### Example 3: Replace Data from JSON

**File**: categories.json
```json
[
  {"id": 1, "name": "Electronics"},
  {"id": 2, "name": "Books"}
]
```

**Steps**:
1. Upload categories.json
2. Select connection and categories table
3. Map columns
4. Choose Truncate & Insert
5. Execute import
6. Result: Old data deleted, 2 new rows inserted

---

## MongoDB Import

For MongoDB, use the MongoDB import tools:
- `mongoimport` command-line tool
- MongoDB Compass GUI
- Or insert via MongoDB Query Interface

---

## Next Steps

- **[Database Connections](database-connections.md)** - Manage connections
- **[SQL Workspace](../getting-started.md#task-2-execute-your-first-sql-query)** - Query imported data
- **[Troubleshooting](../troubleshooting.md#import-errors)** - Import issues

---

**Pro Tip**: Always test imports on a small sample first! 🎯
