"""
MongoDB Query API
Endpoints for executing MongoDB queries and operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from app.database import get_app_db
from app.models.user import User
from app.models.connection import ConnectionProfile, ConnectionType
from app.core.rbac import get_current_user
from app.core.crypto import decrypt_value
from app.connections.connection_manager import connection_manager
from app.services.audit_service import audit_service
from app.models.audit import AuditActionType


router = APIRouter()


# Pydantic models
class MongoDBQueryRequest(BaseModel):
    collection: str
    operation: str  # find, aggregate, count, distinct
    filter: Dict[str, Any] = {}
    projection: Dict[str, Any] = None
    limit: int = 100
    skip: int = 0
    sort: Dict[str, int] = None
    pipeline: list = None  # For aggregation
    field: str = None  # For distinct


@router.post("/connections/{connection_id}/mongodb/query")
async def execute_mongodb_query(
    connection_id: int,
    query: MongoDBQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """
    Execute MongoDB query
    
    Supports operations:
    - find: Query documents with filter, projection, sort, limit
    - aggregate: Run aggregation pipeline
    - count: Count documents matching filter
    - distinct: Get distinct values for a field
    """
    # Get connection profile
    profile = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    if profile.db_type != ConnectionType.MONGODB:
        raise HTTPException(status_code=400, detail="Not a MongoDB connection")
    
    # Check if connection is active
    if not profile.is_active:
        raise HTTPException(status_code=400, detail="Connection is not active")
    
    try:
        # Get connector
        decrypted_password = decrypt_value(profile.encrypted_password)
        connector = connection_manager.get_connector(profile, decrypted_password)
        
        # Build query JSON
        import json
        query_dict = {
            "collection": query.collection,
            "operation": query.operation
        }
        
        if query.operation == "find":
            query_dict["filter"] = query.filter
            if query.projection:
                query_dict["projection"] = query.projection
            query_dict["limit"] = query.limit
            query_dict["skip"] = query.skip
            if query.sort:
                query_dict["sort"] = query.sort
        
        elif query.operation == "aggregate":
            if not query.pipeline:
                raise HTTPException(status_code=400, detail="Pipeline is required for aggregate operation")
            query_dict["pipeline"] = query.pipeline
        
        elif query.operation == "count":
            query_dict["filter"] = query.filter
        
        elif query.operation == "distinct":
            if not query.field:
                raise HTTPException(status_code=400, detail="Field is required for distinct operation")
            query_dict["field"] = query.field
            query_dict["filter"] = query.filter
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {query.operation}")
        
        # Execute query
        query_str = json.dumps(query_dict)
        result = connector.execute_query(query_str)
        
        # Audit log
        await audit_service.log_action(
            db=db,
            user_id=current_user.id,
            action_type=AuditActionType.QUERY_EXECUTE,
            resource_type="mongodb_query",
            connection_id=connection_id,
            connection_name=profile.name,
            action_details={
                "collection": query.collection,
                "operation": query.operation,
                "row_count": result.row_count
            }
        )
        
        return {
            "status": result.status.value,
            "data": result.rows,
            "columns": result.columns,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
            "collection": query.collection,
            "operation": query.operation
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.get("/connections/{connection_id}/mongodb/collections")
async def list_mongodb_collections(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all collections in the MongoDB database"""
    # Get connection profile
    profile = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    if profile.db_type != ConnectionType.MONGODB:
        raise HTTPException(status_code=400, detail="Not a MongoDB connection")
    
    try:
        # Get connector
        decrypted_password = decrypt_value(profile.encrypted_password)
        connector = connection_manager.get_connector(profile, decrypted_password)
        
        # List collections (tables)
        schema = profile.database
        collections = connector.list_tables(schema)
        
        return {
            "collections": [
                {
                    "name": coll.name,
                    "row_count": coll.row_count,
                    "size_bytes": coll.size_bytes
                }
                for coll in collections
            ]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}"
        )
