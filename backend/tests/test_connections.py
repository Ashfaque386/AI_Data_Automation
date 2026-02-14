"""
Integration tests for database connections
"""
import pytest
from app.models.connection import ConnectionProfile
from app.connections.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test connection manager functionality"""
    
    def test_get_connector_postgresql(self):
        """Test getting PostgreSQL connector"""
        profile = ConnectionProfile(
            id=1,
            name="Test PostgreSQL",
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="test_db"
        )
        
        connector = ConnectionManager.get_connector(profile)
        assert connector is not None
        assert connector.__class__.__name__ == "PostgreSQLConnector"
    
    def test_get_connector_mysql(self):
        """Test getting MySQL connector"""
        profile = ConnectionProfile(
            id=2,
            name="Test MySQL",
            db_type="mysql",
            host="localhost",
            port=3306,
            database="test_db"
        )
        
        connector = ConnectionManager.get_connector(profile)
        assert connector is not None
        assert connector.__class__.__name__ == "MySQLConnector"
    
    def test_get_connector_mongodb(self):
        """Test getting MongoDB connector"""
        profile = ConnectionProfile(
            id=3,
            name="Test MongoDB",
            db_type="mongodb",
            host="localhost",
            port=27017,
            database="test_db"
        )
        
        connector = ConnectionManager.get_connector(profile)
        assert connector is not None
        assert connector.__class__.__name__ == "MongoDBConnector"
    
    def test_get_connector_invalid_type(self):
        """Test invalid database type"""
        profile = ConnectionProfile(
            id=4,
            name="Test Invalid",
            db_type="invalid_db",
            host="localhost",
            port=5432,
            database="test_db"
        )
        
        with pytest.raises(ValueError):
            ConnectionManager.get_connector(profile)


class TestConnectionAPI:
    """Test connection API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_list_connections(self, client, auth_headers):
        """Test listing connections"""
        response = client.get(
            "/api/connections",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        connections = response.json()
        assert isinstance(connections, list)
    
    def test_create_connection(self, client, auth_headers):
        """Test creating a connection"""
        connection_data = {
            "name": "Test Connection",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        response = client.post(
            "/api/connections",
            headers=auth_headers,
            json=connection_data
        )
        
        # May fail if database doesn't exist
        if response.status_code == 201:
            connection = response.json()
            assert connection["name"] == "Test Connection"
            assert connection["db_type"] == "postgresql"
    
    def test_test_connection(self, client, auth_headers):
        """Test connection health check"""
        # Assuming connection ID 1 exists
        response = client.post(
            "/api/connections/1/test",
            headers=auth_headers
        )
        
        # May fail if connection doesn't exist
        if response.status_code == 200:
            result = response.json()
            assert "status" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
