"""
Table Entry API Routes
REST endpoints for direct database table data entry.
Uses connection-based selection like Data Import.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, inspect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import structlog

from app.database import get_app_db
from app.models import User, TableEntryAudit, ConnectionProfile
from app.core.rbac import get_current_user
from app.services.table_entry.schema_reader import SchemaReader
from app.services.table_entry.validation_engine import ValidationEngine
from app.services.table_entry.insert_executor import InsertExecutor
from app.services.table_entry.audit_logger import TableEntryAuditLogger
from app.core.crypto import decrypt_value

router = APIRouter()
logger = structlog.get_logger()


# Request/Response Schemas
class TableInfo(BaseModel):
    name: str
    schema: str
    row_count: Optional[int]


class ColumnMetadata(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    foreign_key_ref: Optional[Dict[str, str]]
    is_unique: bool
    autoincrement: bool


class ValidationRequest(BaseModel):
    connection_id: int
    schema: str
    table: str
    rows: List[Dict[str, Any]]


class InsertRequest(BaseModel):
    connection_id: int
    schema: str
    table: str
    rows: List[Dict[str, Any]]
    mode: str = "transaction"  # transaction or row-by-row


# Helper function to get connection profile by ID
def get_connection_profile(db: Session, connection_id: int) -> ConnectionProfile:
    """Get a connection profile by ID."""
    profile = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Connection profile {connection_id} not found"
        )
    
    return profile


# Helper function to create database engine from profile
def create_db_engine(profile: ConnectionProfile):
    """Create a SQLAlchemy engine from a connection profile."""
    password = decrypt_value(profile.encrypted_password) if profile.encrypted_password else ""
    connection_string = f"postgresql://{profile.username}:{password}@{profile.host}:{profile.port}/{profile.database}"
    
    return create_engine(
        connection_string,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 10}
    )


# Endpoints

@router.get("/connections")
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List all available database connections."""
    logger.info("Fetching all connection profiles...")
    connections = db.query(ConnectionProfile).all()
    logger.info(f"Found {len(connections)} connection profiles")
    
    result = {
        "connections": [
            {
                "id": c.id,
                "name": c.name,
                "db_type": c.db_type,
                "host": c.host,
                "database": c.database,
                "is_active": c.is_active
            }
            for c in connections
        ]
    }
    logger.info(f"Returning: {result}")
    return result


@router.get("/connections/{connection_id}/schemas")
async def list_schemas(
    connection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List schemas in the specified connection."""
    try:
        profile = get_connection_profile(db, connection_id)
        engine = create_db_engine(profile)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result]
        
        engine.dispose()
        return {"schemas": schemas}
    except Exception as e:
        logger.error(f"Failed to list schemas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/tables")
async def list_tables(
    connection_id: int,
    schema: str = "public",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """List tables in a schema."""
    try:
        profile = get_connection_profile(db, connection_id)
        engine = create_db_engine(profile)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name,
                       (SELECT reltuples::bigint FROM pg_class WHERE relname = table_name LIMIT 1) as row_count
                FROM information_schema.tables 
                WHERE table_schema = :schema 
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """), {"schema": schema})
            tables = [{"name": row[0], "schema": schema, "row_count": row[1]} for row in result]
        
        engine.dispose()
        return {"tables": tables}
    except Exception as e:
        logger.error(f"Failed to list tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/schema/{schema}/{table}")
async def get_table_schema(
    connection_id: int,
    schema: str,
    table: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get detailed table schema and metadata."""
    try:
        profile = get_connection_profile(db, connection_id)
        reader = SchemaReader(profile)
        
        # Get column metadata
        columns = reader.get_table_schema(schema, table)
        
        # Get constraints
        constraints = reader.get_table_constraints(schema, table)
        
        # Get stats
        stats = reader.get_table_stats(schema, table)
        
        reader.close()
        
        return {
            "schema": schema,
            "table": table,
            "columns": columns,
            "constraints": constraints,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get table schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_rows(
    request: ValidationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Validate rows before insert."""
    try:
        profile = get_connection_profile(db, request.connection_id)
        reader = SchemaReader(profile)
        schema_metadata = reader.get_table_schema(request.schema, request.table)
        
        # Create validation engine
        validator = ValidationEngine(schema_metadata, reader.engine)
        
        # Validate batch
        result = validator.validate_batch(request.rows)
        
        reader.close()
        
        return result
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/reference/{schema}/{table}/{column}")
async def get_foreign_key_values(
    connection_id: int,
    schema: str,
    table: str,
    column: str,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get suggested values for a foreign key column."""
    try:
        profile = get_connection_profile(db, connection_id)
        reader = SchemaReader(profile)
        values = reader.get_foreign_key_values(schema, table, column, search_query=q)
        reader.close()
        return {"values": values}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get FK values: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insert")
async def insert_rows(
    request: InsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Execute insert operation."""
    try:
        profile = get_connection_profile(db, request.connection_id)
        reader = SchemaReader(profile)
        schema_metadata = reader.get_table_schema(request.schema, request.table)
        
        # Validate first
        validator = ValidationEngine(schema_metadata, reader.engine)
        validation_result = validator.validate_batch(request.rows)
        
        if not validation_result['is_valid']:
            reader.close()
            return {
                "success": False,
                "error": "Validation failed",
                "validation_result": validation_result
            }
        
        # Execute insert
        executor = InsertExecutor(reader.engine)
        insert_result = executor.insert_rows(
            request.schema,
            request.table,
            request.rows,
            schema_metadata,
            request.mode
        )
        
        # Log to audit
        TableEntryAuditLogger.log_insert_operation(
            db=db,
            user=current_user,
            connection_id=profile.id,
            schema=request.schema,
            table=request.table,
            rows_attempted=len(request.rows),
            rows_inserted=insert_result['rows_inserted'],
            rows_failed=insert_result['rows_failed'],
            insert_mode=request.mode,
            error_details=insert_result.get('failed_rows')
        )
        
        reader.close()
        
        return insert_result
    except Exception as e:
        logger.error(f"Insert failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit")
async def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_app_db)
):
    """Get table entry audit logs."""
    logs = TableEntryAuditLogger.get_audit_logs(
        db=db,
        user_id=current_user.id,
        connection_id=None,
        limit=limit
    )
    
    return {"logs": logs}
