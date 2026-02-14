# MongoDB Query API Documentation

REST API documentation for MongoDB query operations.

## Base URL

```
http://localhost:8000/api
```

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### 1. Execute MongoDB Query

Execute a MongoDB query operation (find, aggregate, count, distinct).

**Endpoint**: `POST /connections/{connection_id}/mongodb/query`

**Parameters**:
- `connection_id` (path, integer): Database connection ID

**Request Body**:
```json
{
  "collection": "string",
  "operation": "find" | "aggregate" | "count" | "distinct",
  "filter": {},
  "projection": {},
  "sort": {},
  "limit": 100,
  "skip": 0,
  "pipeline": [],
  "field": "string"
}
```

**Response**:
```json
{
  "data": [...],
  "row_count": 10,
  "execution_time_ms": 45.2
}
```

**Example - Find Query**:
```bash
curl -X POST "http://localhost:8000/api/connections/1/mongodb/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "users",
    "operation": "find",
    "filter": {"age": {"$gt": 18}},
    "projection": {"name": 1, "email": 1},
    "limit": 100
  }'
```

**Example - Aggregation**:
```bash
curl -X POST "http://localhost:8000/api/connections/1/mongodb/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "orders",
    "operation": "aggregate",
    "pipeline": [
      {"$match": {"status": "completed"}},
      {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
      {"$sort": {"total": -1}}
    ]
  }'
```

**Example - Count**:
```bash
curl -X POST "http://localhost:8000/api/connections/1/mongodb/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "products",
    "operation": "count",
    "filter": {"price": {"$lt": 100}}
  }'
```

**Example - Distinct**:
```bash
curl -X POST "http://localhost:8000/api/connections/1/mongodb/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "users",
    "operation": "distinct",
    "field": "country",
    "filter": {"active": true}
  }'
```

---

### 2. List Collections

Get all collections in the MongoDB database.

**Endpoint**: `GET /connections/{connection_id}/mongodb/collections`

**Parameters**:
- `connection_id` (path, integer): Database connection ID

**Response**:
```json
[
  {
    "name": "users",
    "row_count": 1523,
    "size_bytes": 245760
  },
  {
    "name": "orders",
    "row_count": 8942,
    "size_bytes": 1048576
  }
]
```

**Example**:
```bash
curl -X GET "http://localhost:8000/api/connections/1/mongodb/collections" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Request Schema

### MongoDBQueryRequest

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection` | string | Yes | Collection name |
| `operation` | string | Yes | Operation type: find, aggregate, count, distinct |
| `filter` | object | No | MongoDB query filter (for find, count, distinct) |
| `projection` | object | No | Field projection (for find) |
| `sort` | object | No | Sort specification (for find) |
| `limit` | integer | No | Maximum documents to return (for find) |
| `skip` | integer | No | Number of documents to skip (for find) |
| `pipeline` | array | No | Aggregation pipeline stages (for aggregate) |
| `field` | string | No | Field name (for distinct) |

### Operation-Specific Fields

**Find Operation**:
- `filter` (optional): Query filter
- `projection` (optional): Fields to include/exclude
- `sort` (optional): Sort order
- `limit` (optional): Max results (default: 100)
- `skip` (optional): Skip documents (default: 0)

**Aggregate Operation**:
- `pipeline` (required): Array of pipeline stages

**Count Operation**:
- `filter` (optional): Query filter

**Distinct Operation**:
- `field` (required): Field name
- `filter` (optional): Query filter

---

## Response Schema

### MongoDBQueryResponse

| Field | Type | Description |
|-------|------|-------------|
| `data` | array | Query results |
| `row_count` | integer | Number of documents returned |
| `execution_time_ms` | float | Query execution time in milliseconds |

### MongoDBCollection

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Collection name |
| `row_count` | integer | Number of documents |
| `size_bytes` | integer | Collection size in bytes |

---

## Error Responses

### 400 Bad Request

Invalid query format or parameters.

```json
{
  "detail": "Invalid JSON in filter field"
}
```

### 403 Forbidden

Insufficient permissions.

```json
{
  "detail": "You don't have permission to query this connection"
}
```

### 404 Not Found

Connection or collection not found.

```json
{
  "detail": "Connection not found"
}
```

### 500 Internal Server Error

Query execution failed.

```json
{
  "detail": "Query execution failed: <error message>"
}
```

---

## Query Examples

### Find with Multiple Conditions

```json
{
  "collection": "users",
  "operation": "find",
  "filter": {
    "age": {"$gte": 18, "$lte": 65},
    "status": "active",
    "country": {"$in": ["US", "CA", "UK"]}
  },
  "projection": {
    "name": 1,
    "email": 1,
    "age": 1
  },
  "sort": {"createdAt": -1},
  "limit": 50
}
```

### Complex Aggregation

```json
{
  "collection": "sales",
  "operation": "aggregate",
  "pipeline": [
    {
      "$match": {
        "date": {"$gte": {"$date": "2024-01-01T00:00:00Z"}}
      }
    },
    {
      "$group": {
        "_id": {
          "year": {"$year": "$date"},
          "month": {"$month": "$date"}
        },
        "revenue": {"$sum": "$amount"},
        "orders": {"$sum": 1},
        "avgOrder": {"$avg": "$amount"}
      }
    },
    {
      "$sort": {"_id.year": -1, "_id.month": -1}
    },
    {
      "$limit": 12
    }
  ]
}
```

### Distinct with Filter

```json
{
  "collection": "products",
  "operation": "distinct",
  "field": "category",
  "filter": {
    "price": {"$gt": 50},
    "inStock": true
  }
}
```

---

## Rate Limiting

- **Limit**: 100 requests per minute per user
- **Header**: `X-RateLimit-Remaining` shows remaining requests
- **Reset**: `X-RateLimit-Reset` shows reset time

---

## Audit Logging

All MongoDB query operations are logged with:
- User ID
- Connection ID
- Operation type
- Collection name
- Execution time
- Timestamp

Access audit logs via Settings → Audit Logs.

---

## Best Practices

✅ **Use projections** to return only needed fields  
✅ **Set reasonable limits** (default: 100, max: 1000)  
✅ **Filter early** in aggregation pipelines  
✅ **Use indexes** for frequently queried fields  
✅ **Handle errors** gracefully in your application  
✅ **Cache results** when appropriate  
✅ **Monitor query performance** via audit logs  

---

## Python Client Example

```python
import requests

# Authentication
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = login_response.json()["access_token"]

# Execute MongoDB query
headers = {"Authorization": f"Bearer {token}"}
query = {
    "collection": "users",
    "operation": "find",
    "filter": {"age": {"$gt": 18}},
    "limit": 100
}

response = requests.post(
    "http://localhost:8000/api/connections/1/mongodb/query",
    headers=headers,
    json=query
)

results = response.json()
print(f"Found {results['row_count']} documents")
print(f"Execution time: {results['execution_time_ms']}ms")
for doc in results['data']:
    print(doc)
```

---

## JavaScript/TypeScript Example

```typescript
// Authentication
const loginResponse = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});
const {access_token} = await loginResponse.json();

// Execute MongoDB query
const query = {
  collection: 'users',
  operation: 'find',
  filter: {age: {$gt: 18}},
  limit: 100
};

const response = await fetch(
  'http://localhost:8000/api/connections/1/mongodb/query',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(query)
  }
);

const results = await response.json();
console.log(`Found ${results.row_count} documents`);
console.log(`Execution time: ${results.execution_time_ms}ms`);
```

---

## Related Documentation

- [MongoDB Query Guide](../features/mongodb-queries.md) - UI-based querying
- [Database Connections](../features/database-connections.md) - Connection management
- [API Reference](http://localhost:8000/docs) - Full API documentation

---

**Need help?** Check the [Troubleshooting Guide](../troubleshooting.md) or contact support.
