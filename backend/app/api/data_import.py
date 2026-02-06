"""
Data Import API
Endpoints for dataset-to-database import workflow
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import structlog

from app.database import get_app_db
from app.models import User, Dataset, ConnectionProfile, ImportJob, ImportMapping
from app.core.rbac import get_current_active_user
from app.services.data_import.import_service import ImportService
from app.services.data_import.execution_engine import ExecutionEngine
from app.core.crypto import decrypt_value

router = APIRouter()
logger = structlog.get_logger()


# Request/Response Models
class ColumnMappingItem(BaseModel):
    source_column: str
    target_column: str
    source_type: str
    target_type: str
    compatible: bool
    transformation: Optional[str] = None
    default_value: Optional[str] = None


class ImportConfigRequest(BaseModel):
    batch_size: int = 1000
    stop_on_error: bool = False
    skip_invalid_rows: bool = False
    pre_import_sql: Optional[str] = None
    post_import_sql: Optional[str] = None


class CreateImportJobRequest(BaseModel):
    dataset_id: int
    connection_id: int
    target_table: str
    target_schema: str = "public"
    import_mode: str  # insert, upsert, truncate_insert
    mappings: List[ColumnMappingItem]
    import_config: ImportConfigRequest


class SaveMappingRequest(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str
    target_table: str
    target_schema: str = "public"
    mappings: List[ColumnMappingItem]
    is_shared: bool = False


# Endpoints

@router.get("/datasets")
async def list_import_datasets(
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List available datasets for import"""
    datasets = db.query(Dataset).filter(
        Dataset.status == "ready"
    ).all()
    
    return {
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "file_type": ds.file_type,
                "row_count": ds.row_count,
                "column_count": len(ds.columns),
                "status": ds.status
            }
            for ds in datasets
        ]
    }


@router.get("/datasets/{dataset_id}/columns")
async def get_dataset_columns(
    dataset_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dataset column information"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "columns": [
            {
                "name": col.name,
                "type": col.data_type,
                "nullable": True  # Datasets are generally nullable
            }
            for col in dataset.columns
        ]
    }


@router.get("/connections")
async def list_import_connections(
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List available database connections for import"""
    connections = db.query(ConnectionProfile).filter(
        ConnectionProfile.is_active == True
    ).all()
    
    return {
        "connections": [
            {
                "id": conn.id,
                "name": conn.name,
                "description": conn.description,
                "db_type": conn.db_type,
                "host": conn.host,
                "port": conn.port,
                "database": conn.database,
                "is_active": conn.is_active
            }
            for conn in connections
        ]
    }


@router.get("/connections/{connection_id}/schemas")
async def list_schemas(
    connection_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List schemas in database connection"""
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        password = decrypt_value(connection.encrypted_password)
        conn_string = (
            f"postgresql://{connection.username}:{password}"
            f"@{connection.host}:{connection.port}/{connection.database}"
        )
        
        exec_engine = ExecutionEngine(conn_string)
        try:
            schemas = exec_engine.list_schemas()
            return {"schemas": schemas}
        finally:
            exec_engine.disconnect()
    
    except Exception as e:
        logger.error("schema_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/tables")
async def list_tables(
    connection_id: int,
    schema: str = "public",
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List tables in schema"""
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        password = decrypt_value(connection.encrypted_password)
        conn_string = (
            f"postgresql://{connection.username}:{password}"
            f"@{connection.host}:{connection.port}/{connection.database}"
        )
        
        exec_engine = ExecutionEngine(conn_string)
        try:
            tables = exec_engine.list_tables(schema)
            return {"tables": tables}
        finally:
            exec_engine.disconnect()
    
    except Exception as e:
        logger.error("table_list_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/tables/{table_name}/columns")
async def get_table_columns(
    connection_id: int,
    table_name: str,
    schema: str = "public",
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get columns from a specific table"""
    connection = db.query(ConnectionProfile).filter(
        ConnectionProfile.id == connection_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    try:
        password = decrypt_value(connection.encrypted_password)
        conn_string = (
            f"postgresql://{connection.username}:{password}"
            f"@{connection.host}:{connection.port}/{connection.database}"
        )
        
        exec_engine = ExecutionEngine(conn_string)
        try:
            columns = exec_engine.get_table_schema(table_name, schema)
            return {"columns": columns}
        finally:
            exec_engine.disconnect()
    
    except Exception as e:
        logger.error("table_columns_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}/schema")
async def get_table_schema(
    table_name: str,
    connection_id: int,
    schema: str = "public",
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get table schema information"""
    import_service = ImportService(db)
    
    try:
        table_info = import_service.get_table_info(connection_id, table_name, schema)
        return table_info
    except Exception as e:
        logger.error("table_schema_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-map")
async def create_auto_mapping(
    dataset_id: int,
    connection_id: int,
    table_name: str,
    schema: str = "public",
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create automatic column mapping"""
    import_service = ImportService(db)
    
    try:
        mapping = import_service.create_auto_mapping(
            dataset_id,
            connection_id,
            table_name,
            schema
        )
        return mapping
    except Exception as e:
        logger.error("auto_mapping_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_import(
    dataset_id: int,
    connection_id: int,
    table_name: str,
    schema: str,
    mappings: List[ColumnMappingItem],
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate import configuration"""
    import_service = ImportService(db)
    
    try:
        validation = import_service.validate_import(
            dataset_id,
            connection_id,
            table_name,
            schema,
            [m.dict() for m in mappings]
        )
        return {
            'mapping_valid': mapping_validation['valid'],
            'mapping_errors': mapping_validation['errors'],
            'mapping_warnings': mapping_validation['warnings']
        }
    except Exception as e:
        logger.error("validation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


class PreviewImportRequest(BaseModel):
    dataset_id: int
    mappings: List[ColumnMappingItem]
    limit: int = 10


@router.post("/preview")
async def preview_import(
    request: PreviewImportRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Preview import data with mappings"""
    import_service = ImportService(db)
    
    try:
        preview_data = import_service.preview_import(
            request.dataset_id,
            [m.dict() for m in request.mappings],
            request.limit
        )
        return {"preview": preview_data}
    except Exception as e:
        logger.error("preview_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs")
async def create_import_job(
    request: CreateImportJobRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create and execute import job"""
    # Create job record
    job = ImportJob(
        user_id=current_user.id,
        dataset_id=request.dataset_id,
        target_connection_id=request.connection_id,
        target_table=request.target_table,
        target_schema=request.target_schema,
        status="pending",
        import_mode=request.import_mode,
        mapping_config={"mappings": [m.dict() for m in request.mappings]},
        import_config=request.import_config.dict()
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Execute import in background
    # TODO: Use background task or celery
    import_service = ImportService(db)
    try:
        result = import_service.execute_import(job.id, current_user.id)
        return {
            "job_id": job.id,
            "status": job.status,
            "result": result
        }
    except Exception as e:
        logger.error("import_execution_failed", job_id=job.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_import_jobs(
    limit: int = 50,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List import jobs"""
    jobs = db.query(ImportJob).filter(
        ImportJob.user_id == current_user.id
    ).order_by(ImportJob.created_at.desc()).limit(limit).all()
    
    return {
        "jobs": [
            {
                "id": job.id,
                "dataset_id": job.dataset_id,
                "target_table": job.target_table,
                "target_schema": job.target_schema,
                "status": job.status,
                "import_mode": job.import_mode,
                "total_rows": job.total_rows,
                "inserted_rows": job.inserted_rows,
                "updated_rows": job.updated_rows,
                "error_rows": job.error_rows,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_import_job(
    job_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get import job details"""
    job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "target_table": job.target_table,
        "target_schema": job.target_schema,
        "status": job.status,
        "import_mode": job.import_mode,
        "total_rows": job.total_rows,
        "inserted_rows": job.inserted_rows,
        "updated_rows": job.updated_rows,
        "error_rows": job.error_rows,
        "error_message": job.error_message,
        "error_details": job.error_details,
        "mapping_config": job.mapping_config,
        "import_config": job.import_config,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    }


@router.post("/mappings")
async def save_mapping_template(
    request: SaveMappingRequest,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save column mapping template"""
    mapping = ImportMapping(
        name=request.name,
        description=request.description,
        user_id=current_user.id,
        source_type=request.source_type,
        target_table=request.target_table,
        target_schema=request.target_schema,
        mapping_config={"mappings": [m.dict() for m in request.mappings]},
        is_shared=1 if request.is_shared else 0
    )
    
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    
    return {"id": mapping.id, "name": mapping.name}


@router.get("/mappings")
async def list_mapping_templates(
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """List saved mapping templates"""
    mappings = db.query(ImportMapping).filter(
        (ImportMapping.user_id == current_user.id) | (ImportMapping.is_shared == 1)
    ).all()
    
    return {
        "mappings": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "source_type": m.source_type,
                "target_table": m.target_table,
                "target_schema": m.target_schema,
                "is_shared": m.is_shared == 1,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in mappings
        ]
    }


@router.delete("/mappings/{mapping_id}")
async def delete_mapping_template(
    mapping_id: int,
    db: Session = Depends(get_app_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete mapping template"""
    mapping = db.query(ImportMapping).filter(
        ImportMapping.id == mapping_id,
        ImportMapping.user_id == current_user.id
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    db.delete(mapping)
    db.commit()
    
    return {"success": True}
