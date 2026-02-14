"""
MongoDB Connector
Implements BaseConnector for MongoDB databases
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import List, Dict, Any, Optional
import json
import time
from datetime import datetime

from app.connections.connectors.base_connector import (
    BaseConnector,
    TableInfo,
    ColumnInfo,
    TableSchema,
    QueryResult,
    QueryResultStatus,
    HealthCheckResult,
    DatabaseCapabilities
)


class MongoDBConnector(BaseConnector):
    """MongoDB connector implementation"""
    
    def __init__(self, connection_string: str, pool_size: int = 5, timeout: int = 30):
        super().__init__(connection_string, pool_size, timeout)
        self.client: Optional[MongoClient] = None
        self.db = None
        self._db_name = None
        
        # Extract database name from connection string
        if '/' in connection_string:
            parts = connection_string.split('/')
            if len(parts) > 0:
                # Get the part after the last slash as potential db name
                last_part = parts[-1] 
                # Remove query parameters
                db_name = last_part.split('?')[0]
                if db_name:
                    self._db_name = db_name
    
    def connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=self.timeout * 1000,
                connectTimeoutMS=self.timeout * 1000,
                maxPoolSize=self.pool_size
            )
            
            # Get database
            if self._db_name:
                self.db = self.client[self._db_name]
            else:
                try:
                    # Try to get default database from URI
                    self.db = self.client.get_default_database()
                    self._db_name = self.db.name
                except Exception:
                    # Fallback to 'admin' if no default database is defined
                    # This allows connection to succeed for listing databases or server admin tasks
                    self.db = self.client['admin']
                    self._db_name = 'admin'
            
            self._connection = self.client  # Set for is_connected() check
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self._connection = None
    
    def test_connection(self) -> HealthCheckResult:
        """Test MongoDB connection"""
        start_time = time.time()
        try:
            if not self.client:
                self.connect()
            
            # Ping the database
            self.client.admin.command('ping')
            
            response_time_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                is_healthy=True,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                is_healthy=False,
                response_time_ms=response_time_ms,
                error_message=str(e),
                timestamp=datetime.utcnow()
            )
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        Execute MongoDB query (JSON format, not SQL)
        
        Query format: JSON string representing MongoDB operation
        Example: 
        {
            "collection": "users",
            "operation": "find",
            "filter": {"age": {"$gt": 18}},
            "projection": {"name": 1, "email": 1},
            "limit": 100
        }
        """
        start_time = time.time()
        try:
            if not self.client:
                self.connect()
            
            # Parse query as JSON
            query_obj = json.loads(sql)
            
            collection_name = query_obj.get('collection')
            operation = query_obj.get('operation', 'find')
            
            if not collection_name:
                raise ValueError("Collection name is required in query")
            
            collection = self.db[collection_name]
            
            # Execute based on operation type
            if operation == 'find':
                results = self._execute_find(collection, query_obj)
            elif operation == 'aggregate':
                results = self._execute_aggregate(collection, query_obj)
            elif operation == 'count':
                results = self._execute_count(collection, query_obj)
            elif operation == 'distinct':
                results = self._execute_distinct(collection, query_obj)
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Convert to QueryResult format
            columns = list(results[0].keys()) if results else []
            
            return QueryResult(
                status=QueryResultStatus.SUCCESS,
                rows=results,
                columns=columns,
                row_count=len(results),
                execution_time_ms=execution_time_ms
            )
        
        except json.JSONDecodeError as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return QueryResult(
                status=QueryResultStatus.ERROR,
                rows=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error_message=f"Invalid JSON query: {str(e)}"
            )
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return QueryResult(
                status=QueryResultStatus.ERROR,
                rows=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error_message=f"Query execution failed: {str(e)}"
            )
    
    def execute_ddl(self, sql: str) -> bool:
        """MongoDB doesn't support DDL in the traditional sense"""
        raise NotImplementedError("DDL operations are not supported for MongoDB")
    
    def list_databases(self) -> List[str]:
        """List all MongoDB databases."""
        if not self.client:
            self.connect()
        return self.client.list_database_names()
    
    def list_schemas(self) -> List[str]:
        """List databases (MongoDB equivalent of schemas)"""
        if not self.client:
            self.connect()
        return [self._db_name] if self._db_name else []
    
    def list_tables(self, schema: str) -> List[TableInfo]:
        """List collections (MongoDB equivalent of tables)"""
        if not self.client:
            self.connect()
        
        collections = self.db.list_collection_names()
        
        table_infos = []
        for collection_name in collections:
            try:
                # Get collection stats
                stats = self.db.command("collStats", collection_name)
                
                table_infos.append(TableInfo(
                    name=collection_name,
                    schema=self._db_name,
                    table_type="collection",
                    row_count=stats.get('count', 0),
                    size_bytes=stats.get('size', 0)
                ))
            except Exception:
                # If stats fail, still add the collection with minimal info
                table_infos.append(TableInfo(
                    name=collection_name,
                    schema=self._db_name,
                    table_type="collection"
                ))
        
        return table_infos
    
    def get_table_schema(self, table: str, schema: str) -> TableSchema:
        """Get collection schema (inferred from sample documents)"""
        if not self.client:
            self.connect()
        
        collection = self.db[table]
        
        # Sample a few documents to infer schema
        sample_docs = list(collection.find().limit(10))
        
        # Collect all unique fields
        fields = set()
        for doc in sample_docs:
            fields.update(doc.keys())
        
        # Create column info for each field
        columns = []
        for field in sorted(fields):
            columns.append(ColumnInfo(
                name=field,
                data_type="mixed",  # MongoDB has dynamic types
                is_nullable=True
            ))
        
        return TableSchema(
            table_name=table,
            schema_name=schema,
            columns=columns,
            primary_keys=["_id"],  # MongoDB always has _id
            foreign_keys=[],
            indexes=[]
        )
    
    def start_transaction(self) -> None:
        """Begin a new transaction (MongoDB 4.0+)"""
        # MongoDB transactions require replica sets
        # For simplicity, we'll pass for now
        pass
    
    def commit(self) -> None:
        """Commit current transaction"""
        pass
    
    def rollback(self) -> None:
        """Rollback current transaction"""
        pass
    
    def detect_capabilities(self) -> DatabaseCapabilities:
        """Detect MongoDB capabilities"""
        if not self.client:
            self.connect()
        
        server_info = self.client.server_info()
        version = server_info.get('version', 'Unknown')
        
        return DatabaseCapabilities(
            version=version,
            supports_transactions=True,  # MongoDB 4.0+
            supports_stored_procedures=False,
            supports_views=True,
            supports_materialized_views=False,
            supports_json=True,  # Native JSON/BSON
            supports_full_text_search=True,
            max_connections=100,  # Default
            features=["Document Store", "Aggregation Pipeline", "Geospatial", "Text Search"],
            extensions=[]
        )
    
    # Helper methods for MongoDB operations
    def _execute_find(self, collection, query_obj: Dict) -> List[Dict]:
        """Execute find operation"""
        filter_query = query_obj.get('filter', {})
        projection = query_obj.get('projection')
        limit = query_obj.get('limit', 100)
        skip = query_obj.get('skip', 0)
        sort = query_obj.get('sort')
        
        cursor = collection.find(filter_query, projection)
        
        if skip > 0:
            cursor = cursor.skip(skip)
        
        if sort:
            cursor = cursor.sort(list(sort.items()))
        
        cursor = cursor.limit(limit)
        
        results = list(cursor)
        
        # Convert ObjectId and datetime to strings
        return self._serialize_documents(results)
    
    def _execute_aggregate(self, collection, query_obj: Dict) -> List[Dict]:
        """Execute aggregation pipeline"""
        pipeline = query_obj.get('pipeline', [])
        
        if not isinstance(pipeline, list):
            raise ValueError("Pipeline must be a list of stages")
        
        results = list(collection.aggregate(pipeline))
        
        return self._serialize_documents(results)
    
    def _execute_count(self, collection, query_obj: Dict) -> List[Dict]:
        """Execute count operation"""
        filter_query = query_obj.get('filter', {})
        count = collection.count_documents(filter_query)
        
        return [{"count": count}]
    
    def _execute_distinct(self, collection, query_obj: Dict) -> List[Dict]:
        """Execute distinct operation"""
        field = query_obj.get('field')
        filter_query = query_obj.get('filter', {})
        
        if not field:
            raise ValueError("Field is required for distinct operation")
        
        distinct_values = collection.distinct(field, filter_query)
        
        # Convert to list of dicts
        return [{field: value} for value in distinct_values]
    
    def _serialize_documents(self, documents: List[Dict]) -> List[Dict]:
        """Convert MongoDB documents to JSON-serializable format"""
        from bson import ObjectId
        
        def serialize_value(value):
            if isinstance(value, ObjectId):
                return str(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            else:
                return value
        
        return [serialize_value(doc) for doc in documents]
