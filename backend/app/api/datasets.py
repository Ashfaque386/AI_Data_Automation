"""
Dataset API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json

from app.database import get_db
from app.schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse, DatasetListResponse,
    DatasetVersionResponse, DataGridRequest, DataGridResponse, 
    BulkUpdateRequest, UploadConfig, ColumnStats
)
from app.models import Dataset, User, DatasetStatus
from app.core.rbac import get_current_user, DatasetAccessChecker
from app.core.audit import AuditLogger
from app.services import FileIngestionService

router = APIRouter()


@router.get("/", response_model=List[DatasetListResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all accessible datasets."""
    # Get datasets owned by user or public
    query = db.query(Dataset).filter(
        (Dataset.owner_id == current_user.id) | (Dataset.is_public == True)
    )
    
    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    return datasets


@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    dataset_data: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new empty dataset."""
    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        owner_id=current_user.id,
        status=DatasetStatus.READY.value,
        source_type="manual"
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return dataset


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Query(...),
    description: Optional[str] = Query(None),
    config: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file and create a dataset."""
    # Parse config if provided
    upload_config = {}
    if config:
        try:
            upload_config = json.loads(config)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid config JSON"
            )
    
    # Read file content
    file_content = await file.read()
    
    # Ingest file
    ingestion_service = FileIngestionService(db)
    try:
        dataset = ingestion_service.ingest_file(
            file_content=file_content,
            filename=file.filename,
            dataset_name=name,
            owner_id=current_user.id,
            description=description,
            config=upload_config
        )
        dataset_id = dataset.id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File ingestion failed: {str(e)}"
        )
    
    # Query the dataset fresh with all relationships
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dataset created but could not be retrieved"
        )
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_upload(
        user=current_user,
        dataset_name=dataset.name,
        dataset_id=dataset.id,
        file_type=dataset.file_type,
        row_count=dataset.row_count
    )
    
    return dataset



@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dataset by ID."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check access
    if not DatasetAccessChecker.can_read(db, current_user, dataset):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this dataset"
        )
    
    return dataset


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int,
    dataset_update: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update dataset metadata."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check access
    if not DatasetAccessChecker.can_write(db, current_user, dataset):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No write access to this dataset"
        )
    
    # Update fields
    if dataset_update.name:
        dataset.name = dataset_update.name
    if dataset_update.description is not None:
        dataset.description = dataset_update.description
    if dataset_update.is_public is not None and dataset.owner_id == current_user.id:
        dataset.is_public = dataset_update.is_public
    if dataset_update.is_locked is not None and dataset.owner_id == current_user.id:
        dataset.is_locked = dataset_update.is_locked
    
    db.commit()
    db.refresh(dataset)
    
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check access
    if not DatasetAccessChecker.can_delete(db, current_user, dataset):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No delete access to this dataset"
        )
    
    db.delete(dataset)
    db.commit()
    
    return {"message": "Dataset deleted successfully"}


@router.post("/{dataset_id}/data", response_model=DataGridResponse)
async def get_dataset_data(
    dataset_id: int,
    request: DataGridRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get paginated dataset data."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check access
    if not DatasetAccessChecker.can_read(db, current_user, dataset):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this dataset"
        )
    
    # Get data from DuckDB (NaN/Inf handled in SQL engine)
    from app.services import SQLEngine, FileIngestionService
    sql_engine = SQLEngine(db)
    
    # Check if table exists in DuckDB, if not, load it
    check_query = f"SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_name = '{dataset.virtual_table_name}'"
    check_result = sql_engine.execute(check_query)
    
    table_exists = False
    if check_result.success and check_result.data and len(check_result.data) > 0:
        table_exists = check_result.data[0].get('cnt', 0) > 0
    
    if not table_exists:
        # Load dataset into DuckDB
        ingestion_service = FileIngestionService(db)
        loaded = ingestion_service.load_dataset_to_duckdb(dataset)
        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load dataset into memory"
            )
    
    # Build query
    columns = ", ".join(request.columns) if request.columns else "*"
    query = f"SELECT {columns} FROM {dataset.virtual_table_name}"
    
    # Add filters
    if request.filters:
        conditions = []
        for col, val in request.filters.items():
            if isinstance(val, str):
                conditions.append(f"{col} = '{val}'")
            else:
                conditions.append(f"{col} = {val}")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    # Add sorting
    if request.sort_by:
        query += f" ORDER BY {request.sort_by} {'DESC' if request.sort_desc else 'ASC'}"
    
    # Add pagination
    offset = (request.page - 1) * request.page_size
    query += f" LIMIT {request.page_size} OFFSET {offset}"
    
    # Execute query
    result = sql_engine.execute(query)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {result.error_message}"
        )
    
    # Get total count
    count_query = f"SELECT COUNT(*) as total FROM {dataset.virtual_table_name}"
    count_result = sql_engine.execute(count_query)
    total_rows = count_result.data[0]['total'] if count_result.success else 0
    
    return DataGridResponse(
        data=result.data,
        total_rows=total_rows,
        page=request.page,
        page_size=request.page_size,
        total_pages=(total_rows + request.page_size - 1) // request.page_size,
        columns=dataset.columns
    )


@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
async def get_dataset_versions(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dataset version history."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    # Check access
    if not DatasetAccessChecker.can_read(db, current_user, dataset):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this dataset"
        )
    
    return dataset.versions
