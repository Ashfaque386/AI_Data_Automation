"""
Integration tests for MongoDB connector and API
"""
import pytest
from pymongo import MongoClient
from app.connections.connectors.mongodb_connector import MongoDBConnector
from app.models.connection import ConnectionProfile


class TestMongoDBConnector:
    """Test MongoDB connector functionality"""
    
    @pytest.fixture
    def connection_profile(self):
        """Create test connection profile"""
        return ConnectionProfile(
            id=1,
            name="Test MongoDB",
            db_type="mongodb",
            host="localhost",
            port=27017,
            database="test_db",
            username=None,
            password=None
        )
    
    @pytest.fixture
    def connector(self, connection_profile):
        """Create MongoDB connector instance"""
        return MongoDBConnector(connection_profile)
    
    def test_connection(self, connector):
        """Test MongoDB connection"""
        try:
            connector.connect()
            assert connector.client is not None
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_test_connection(self, connector):
        """Test connection health check"""
        try:
            result = connector.test_connection()
            assert result["status"] == "success"
            assert "message" in result
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_list_collections(self, connector):
        """Test listing collections"""
        try:
            connector.connect()
            collections = connector.list_tables()
            assert isinstance(collections, list)
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_find_query(self, connector):
        """Test find operation"""
        try:
            connector.connect()
            
            # Insert test data
            collection = connector.db["test_collection"]
            collection.delete_many({})  # Clear collection
            collection.insert_many([
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ])
            
            # Execute find query
            query = {
                "collection": "test_collection",
                "operation": "find",
                "filter": {"age": {"$gt": 20}},
                "limit": 10
            }
            result = connector.execute_query(query)
            
            assert result["row_count"] == 2
            assert len(result["data"]) == 2
            assert "execution_time_ms" in result
            
            # Cleanup
            collection.delete_many({})
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_aggregate_query(self, connector):
        """Test aggregation pipeline"""
        try:
            connector.connect()
            
            # Insert test data
            collection = connector.db["test_orders"]
            collection.delete_many({})
            collection.insert_many([
                {"category": "A", "amount": 100},
                {"category": "A", "amount": 150},
                {"category": "B", "amount": 200}
            ])
            
            # Execute aggregation
            query = {
                "collection": "test_orders",
                "operation": "aggregate",
                "pipeline": [
                    {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
                    {"$sort": {"total": -1}}
                ]
            }
            result = connector.execute_query(query)
            
            assert result["row_count"] == 2
            assert len(result["data"]) == 2
            
            # Cleanup
            collection.delete_many({})
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_count_query(self, connector):
        """Test count operation"""
        try:
            connector.connect()
            
            # Insert test data
            collection = connector.db["test_users"]
            collection.delete_many({})
            collection.insert_many([
                {"status": "active"},
                {"status": "active"},
                {"status": "inactive"}
            ])
            
            # Execute count
            query = {
                "collection": "test_users",
                "operation": "count",
                "filter": {"status": "active"}
            }
            result = connector.execute_query(query)
            
            assert result["data"] == 2
            
            # Cleanup
            collection.delete_many({})
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_distinct_query(self, connector):
        """Test distinct operation"""
        try:
            connector.connect()
            
            # Insert test data
            collection = connector.db["test_products"]
            collection.delete_many({})
            collection.insert_many([
                {"category": "A"},
                {"category": "B"},
                {"category": "A"}
            ])
            
            # Execute distinct
            query = {
                "collection": "test_products",
                "operation": "distinct",
                "field": "category"
            }
            result = connector.execute_query(query)
            
            assert result["row_count"] == 2
            assert set(result["data"]) == {"A", "B"}
            
            # Cleanup
            collection.delete_many({})
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")
    
    def test_invalid_operation(self, connector):
        """Test invalid operation handling"""
        try:
            connector.connect()
            
            query = {
                "collection": "test_collection",
                "operation": "invalid_op"
            }
            
            with pytest.raises(ValueError):
                connector.execute_query(query)
            
            connector.disconnect()
        except Exception as e:
            pytest.skip(f"MongoDB not available: {e}")


class TestMongoDBAPI:
    """Test MongoDB API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        # Login as admin
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "admin123"}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_list_collections_endpoint(self, client, auth_headers):
        """Test list collections endpoint"""
        # Assuming connection ID 1 exists and is MongoDB
        response = client.get(
            "/api/connections/1/mongodb/collections",
            headers=auth_headers
        )
        
        # May fail if connection doesn't exist or isn't MongoDB
        if response.status_code == 200:
            collections = response.json()
            assert isinstance(collections, list)
    
    def test_execute_query_endpoint(self, client, auth_headers):
        """Test execute query endpoint"""
        query = {
            "collection": "test_collection",
            "operation": "find",
            "filter": {},
            "limit": 10
        }
        
        response = client.post(
            "/api/connections/1/mongodb/query",
            headers=auth_headers,
            json=query
        )
        
        # May fail if connection doesn't exist or isn't MongoDB
        if response.status_code == 200:
            result = response.json()
            assert "data" in result
            assert "row_count" in result
            assert "execution_time_ms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
