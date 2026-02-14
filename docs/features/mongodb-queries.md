# MongoDB Query Guide

Complete guide to querying MongoDB databases using the AI Data Automation Platform.

## Overview

The MongoDB Query Interface provides a user-friendly way to execute MongoDB queries without writing code. It supports all major MongoDB operations with visual query builders and JSON editors.

---

## Getting Started

### Creating a MongoDB Connection

1. Navigate to **Database Connections**
2. Click **+ Add Connection**
3. Select **MongoDB** as database type
4. Enter connection details:
   - **Name**: Descriptive name (e.g., "Production MongoDB")
   - **Host**: MongoDB server address
   - **Port**: 27017 (default)
   - **Database**: Database name
   - **Username/Password**: Authentication credentials (if required)
5. Click **Test Connection**
6. If successful, click **Save**

### Opening the Query Interface

1. Go to **Database Connections**
2. Find your MongoDB connection
3. Click the **🍃 Query** button
4. The MongoDB Query Interface will open

---

## Query Operations

### 1. Find Documents

Retrieve documents from a collection with optional filtering, projection, and limits.

**Use Case**: Get all active users over age 18

**Steps**:
1. Select **Collection**: `users`
2. Click **Find** tab
3. Enter **Filter**:
   ```json
   {
     "age": {"$gt": 18},
     "status": "active"
   }
   ```
4. Enter **Projection** (optional):
   ```json
   {
     "name": 1,
     "email": 1,
     "age": 1,
     "_id": 0
   }
   ```
5. Set **Limit**: `100`
6. Click **▶ Execute Query**

**Common Filters**:

```json
// Exact match
{"status": "active"}

// Greater than
{"age": {"$gt": 18}}

// Less than or equal
{"price": {"$lte": 100}}

// In array
{"category": {"$in": ["electronics", "books"]}}

// Not equal
{"status": {"$ne": "deleted"}}

// AND condition
{"age": {"$gt": 18}, "status": "active"}

// OR condition
{"$or": [{"status": "active"}, {"status": "pending"}]}

// Regex match
{"name": {"$regex": "^John", "$options": "i"}}

// Exists
{"email": {"$exists": true}}

// Array contains
{"tags": {"$in": ["featured"]}}
```

### 2. Aggregation Pipeline

Perform complex data transformations and analytics.

**Use Case**: Count orders by category and sort by total

**Steps**:
1. Select **Collection**: `orders`
2. Click **Aggregate** tab
3. Enter **Pipeline**:
   ```json
   [
     {
       "$match": {
         "status": "completed"
       }
     },
     {
       "$group": {
         "_id": "$category",
         "total": {"$sum": "$amount"},
         "count": {"$sum": 1}
       }
     },
     {
       "$sort": {
         "total": -1
       }
     },
     {
       "$limit": 10
     }
   ]
   ```
4. Click **▶ Execute Query**

**Common Pipeline Stages**:

```json
// $match - Filter documents
{"$match": {"status": "active"}}

// $group - Group and aggregate
{
  "$group": {
    "_id": "$category",
    "total": {"$sum": "$amount"},
    "avg": {"$avg": "$price"},
    "count": {"$sum": 1}
  }
}

// $sort - Sort results
{"$sort": {"createdAt": -1}}

// $limit - Limit results
{"$limit": 100}

// $skip - Skip documents
{"$skip": 20}

// $project - Select fields
{
  "$project": {
    "name": 1,
    "email": 1,
    "fullName": {"$concat": ["$firstName", " ", "$lastName"]}
  }
}

// $lookup - Join collections
{
  "$lookup": {
    "from": "orders",
    "localField": "_id",
    "foreignField": "userId",
    "as": "userOrders"
  }
}

// $unwind - Deconstruct array
{"$unwind": "$tags"}

// $addFields - Add computed fields
{
  "$addFields": {
    "totalPrice": {"$multiply": ["$quantity", "$price"]}
  }
}
```

**Example Pipelines**:

**Sales by Month**:
```json
[
  {
    "$group": {
      "_id": {
        "year": {"$year": "$createdAt"},
        "month": {"$month": "$createdAt"}
      },
      "revenue": {"$sum": "$amount"},
      "orders": {"$sum": 1}
    }
  },
  {
    "$sort": {"_id.year": -1, "_id.month": -1}
  }
]
```

**Top Customers**:
```json
[
  {
    "$group": {
      "_id": "$customerId",
      "totalSpent": {"$sum": "$amount"},
      "orderCount": {"$sum": 1}
    }
  },
  {
    "$sort": {"totalSpent": -1}
  },
  {
    "$limit": 10
  },
  {
    "$lookup": {
      "from": "customers",
      "localField": "_id",
      "foreignField": "_id",
      "as": "customer"
    }
  }
]
```

### 3. Count Documents

Count documents matching a filter.

**Use Case**: Count active products under $100

**Steps**:
1. Select **Collection**: `products`
2. Click **Count** tab
3. Enter **Filter**:
   ```json
   {
     "status": "active",
     "price": {"$lt": 100}
   }
   ```
4. Click **▶ Execute Query**

**Result**: Returns count as a number

### 4. Distinct Values

Get unique values for a field.

**Use Case**: Get all unique countries from users

**Steps**:
1. Select **Collection**: `users`
2. Click **Distinct** tab
3. Enter **Field**: `country`
4. Enter **Filter** (optional):
   ```json
   {"status": "active"}
   ```
5. Click **▶ Execute Query**

**Result**: Returns array of unique values

---

## Working with Results

### JSON Tree Viewer

Results are displayed in an interactive JSON tree viewer:

**Features**:
- **Expand/Collapse**: Click ▶/▼ to expand/collapse objects and arrays
- **Syntax Highlighting**: Color-coded by data type
- **Copy**: Click 📋 Copy to copy results to clipboard
- **Download**: Click 💾 Download to save as JSON file
- **View Modes**: 
  - **Pretty**: Collapsible tree view
  - **Compact**: Raw JSON

### Result Metadata

Each query shows:
- **Document Count**: Number of documents returned
- **Execution Time**: Query execution time in milliseconds

---

## Advanced Techniques

### Working with Dates

```json
// Current date
{"createdAt": {"$gte": {"$date": "2024-01-01T00:00:00Z"}}}

// Date range
{
  "createdAt": {
    "$gte": {"$date": "2024-01-01T00:00:00Z"},
    "$lt": {"$date": "2024-02-01T00:00:00Z"}
  }
}

// Last 30 days (use aggregation)
{
  "$expr": {
    "$gte": [
      "$createdAt",
      {"$subtract": [new Date(), 30 * 24 * 60 * 60 * 1000]}
    ]
  }
}
```

### Working with Arrays

```json
// Array contains value
{"tags": "featured"}

// Array contains any of values
{"tags": {"$in": ["featured", "popular"]}}

// Array size
{"tags": {"$size": 3}}

// All elements match
{"tags": {"$all": ["featured", "popular"]}}

// Element match (complex)
{
  "items": {
    "$elemMatch": {
      "price": {"$gt": 100},
      "quantity": {"$gte": 2}
    }
  }
}
```

### Text Search

```json
// Text search (requires text index)
{"$text": {"$search": "mongodb query"}}

// Case-insensitive regex
{"name": {"$regex": "john", "$options": "i"}}
```

### Geospatial Queries

```json
// Near location (requires 2dsphere index)
{
  "location": {
    "$near": {
      "$geometry": {
        "type": "Point",
        "coordinates": [-73.9667, 40.78]
      },
      "$maxDistance": 5000
    }
  }
}
```

---

## Best Practices

### Performance Tips

✅ **Use indexes** for frequently queried fields  
✅ **Limit results** with `$limit` to avoid large result sets  
✅ **Use projection** to return only needed fields  
✅ **Filter early** in aggregation pipelines with `$match`  
✅ **Avoid** `$lookup` on large collections when possible  

### Query Optimization

```json
// ❌ Bad: No limit, returns all documents
{"status": "active"}

// ✅ Good: Limited results
{"status": "active"} // with Limit: 100

// ❌ Bad: $lookup before $match
[
  {"$lookup": {...}},
  {"$match": {"status": "active"}}
]

// ✅ Good: $match before $lookup
[
  {"$match": {"status": "active"}},
  {"$lookup": {...}}
]
```

### Security

✅ **Use read-only credentials** for query-only connections  
✅ **Limit database access** to specific collections  
✅ **Avoid exposing** sensitive data in projections  
✅ **Review audit logs** for suspicious queries  

---

## Troubleshooting

### Query Errors

**Invalid JSON**:
- Check for missing commas, brackets, or quotes
- Use a JSON validator

**Field not found**:
- Verify field names (case-sensitive)
- Check document structure

**Timeout**:
- Add indexes to queried fields
- Reduce result set with filters
- Increase timeout in connection settings

### Connection Issues

**Authentication failed**:
- Verify username and password
- Check authentication database
- Ensure user has required permissions

**Cannot connect**:
- Check host and port
- Verify MongoDB is running
- Check firewall rules
- Use `host.docker.internal` for local MongoDB

---

## Example Queries

### E-commerce Analytics

**Daily Sales**:
```json
[
  {
    "$match": {
      "status": "completed",
      "createdAt": {"$gte": {"$date": "2024-01-01T00:00:00Z"}}
    }
  },
  {
    "$group": {
      "_id": {
        "$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt"}
      },
      "revenue": {"$sum": "$amount"},
      "orders": {"$sum": 1}
    }
  },
  {
    "$sort": {"_id": -1}
  }
]
```

**Product Performance**:
```json
[
  {
    "$group": {
      "_id": "$productId",
      "totalSales": {"$sum": "$amount"},
      "unitsSold": {"$sum": "$quantity"},
      "avgPrice": {"$avg": "$price"}
    }
  },
  {
    "$sort": {"totalSales": -1}
  },
  {
    "$limit": 20
  }
]
```

### User Analytics

**Active Users by Country**:
```json
[
  {
    "$match": {"status": "active"}
  },
  {
    "$group": {
      "_id": "$country",
      "users": {"$sum": 1}
    }
  },
  {
    "$sort": {"users": -1}
  }
]
```

**User Engagement**:
```json
[
  {
    "$group": {
      "_id": "$userId",
      "sessions": {"$sum": 1},
      "totalDuration": {"$sum": "$duration"},
      "lastActive": {"$max": "$timestamp"}
    }
  },
  {
    "$match": {"sessions": {"$gte": 5}}
  },
  {
    "$sort": {"totalDuration": -1}
  }
]
```

---

## Next Steps

- **[Database Connections Guide](database-connections.md)** - Advanced connection management
- **[Data Import Guide](data-import.md)** - Import data into MongoDB
- **[Security & Permissions](security-permissions.md)** - Access control for MongoDB

---

## MongoDB Resources

- [MongoDB Query Operators](https://docs.mongodb.com/manual/reference/operator/query/)
- [Aggregation Pipeline Stages](https://docs.mongodb.com/manual/reference/operator/aggregation-pipeline/)
- [MongoDB Indexes](https://docs.mongodb.com/manual/indexes/)
- [MongoDB Best Practices](https://docs.mongodb.com/manual/administration/production-notes/)
