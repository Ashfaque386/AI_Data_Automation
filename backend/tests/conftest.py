# Test Configuration
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test database URL (use separate test database)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/test_ai_data_management"
)

# Test MongoDB URL
TEST_MONGODB_URL = os.getenv(
    "TEST_MONGODB_URL",
    "mongodb://localhost:27017/test_db"
)

# Test settings
TEST_SECRET_KEY = "test-secret-key-for-testing-only"
TEST_ALGORITHM = "HS256"
TEST_ACCESS_TOKEN_EXPIRE_MINUTES = 30
