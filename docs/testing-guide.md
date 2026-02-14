# Testing Guide

Guide for running tests on the AI Data Automation Platform.

## Setup

### Install Test Dependencies

```powershell
# From backend directory
cd backend
pip install -r tests/requirements-test.txt
```

Or install in Docker:
```powershell
docker exec -it dataops_backend pip install -r tests/requirements-test.txt
```

---

## Running Tests

### All Tests

```powershell
# From backend directory
pytest tests/ -v
```

### Specific Test File

```powershell
pytest tests/test_mongodb.py -v
```

### Specific Test Class

```powershell
pytest tests/test_mongodb.py::TestMongoDBConnector -v
```

### Specific Test Method

```powershell
pytest tests/test_mongodb.py::TestMongoDBConnector::test_find_query -v
```

### With Coverage

```powershell
pytest tests/ --cov=app --cov-report=html
```

View coverage report:
```powershell
# Open htmlcov/index.html in browser
start htmlcov/index.html
```

---

## Test Structure

```
backend/tests/
├── conftest.py              # Test configuration
├── requirements-test.txt    # Test dependencies
├── test_mongodb.py          # MongoDB tests
├── test_connections.py      # Connection tests
└── test_queries.py          # Query tests (future)
```

---

## Test Configuration

### Environment Variables

Set test database URLs:
```powershell
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
$env:TEST_MONGODB_URL="mongodb://localhost:27017/test_db"
```

### Test Database Setup

**PostgreSQL**:
```sql
CREATE DATABASE test_ai_data_management;
```

**MongoDB**:
```powershell
# MongoDB will create database automatically
mongosh
use test_db
```

---

## Writing Tests

### Test Structure

```python
import pytest

class TestFeature:
    """Test feature functionality"""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        # Setup code
        yield data
        # Teardown code
    
    def test_something(self, setup_data):
        """Test description"""
        # Arrange
        input_data = setup_data
        
        # Act
        result = function(input_data)
        
        # Assert
        assert result == expected
```

### Fixtures

Use fixtures for reusable setup:
```python
@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    response = client.post("/api/auth/login", json={...})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Skipping Tests

Skip tests when dependencies unavailable:
```python
def test_mongodb_connection(connector):
    try:
        connector.connect()
        assert connector.client is not None
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")
```

---

## Test Coverage

### Current Coverage

- MongoDB connector: ✅ Comprehensive
- Connection manager: ✅ Basic
- API endpoints: ✅ Basic
- Authentication: ⏳ TODO
- RBAC: ⏳ TODO
- Data import: ⏳ TODO

### Coverage Goals

- Backend: 70%+
- Critical paths: 90%+
- MongoDB features: 90%+

---

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
      
      mongodb:
        image: mongo:7
        ports:
          - 27017:27017
    
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/tests/requirements-test.txt
      - name: Run tests
        run: pytest backend/tests/ --cov=backend/app
```

---

## Troubleshooting

### Tests Fail to Import

**Solution**:
```powershell
# Ensure PYTHONPATH is set
$env:PYTHONPATH="D:\AI_Data_Automation\backend"
pytest tests/
```

### Database Connection Fails

**Check**:
- Database is running
- Test database exists
- Credentials are correct
- TEST_DATABASE_URL is set

### MongoDB Tests Skipped

**Reason**: MongoDB not available

**Solution**:
- Install and start MongoDB
- Set TEST_MONGODB_URL
- Verify connection: `mongosh`

---

## Best Practices

✅ **Isolate tests** - Each test should be independent  
✅ **Use fixtures** - Reuse setup code  
✅ **Clean up** - Remove test data after tests  
✅ **Skip gracefully** - Skip when dependencies unavailable  
✅ **Test edge cases** - Not just happy path  
✅ **Use descriptive names** - Test names should explain what they test  
✅ **Keep tests fast** - Use mocks for slow operations  

---

## Next Steps

1. Run existing tests
2. Add more test coverage
3. Set up CI/CD
4. Add performance tests
5. Add E2E tests

---

**Happy Testing!** 🧪
