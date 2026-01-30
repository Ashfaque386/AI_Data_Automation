"""
Export API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import pandas as pd

from app.database import get_db
from app.models import Dataset, User
from app.core.rbac import get_current_user, DatasetAccessChecker
from app.core.audit import AuditLogger
from app.services import FileIngestionService

router = APIRouter()


async def get_dataset_for_export(
    dataset_id: int,
    current_user: User,
    db: Session
) -> Dataset:
    """Get dataset and check export permissions."""
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


@router.get("/excel/{dataset_id}")
async def export_to_excel(
    dataset_id: int,
    sheet_name: Optional[str] = Query("Sheet1"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export dataset to Excel."""
    if not current_user.has_permission("export:excel"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Excel export permission required"
        )
    
    dataset = await get_dataset_for_export(dataset_id, current_user, db)
    
    # Get data
    ingestion_service = FileIngestionService(db)
    df = ingestion_service.get_dataset_dataframe(dataset)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_export(
        user=current_user,
        dataset_name=dataset.name,
        dataset_id=dataset.id,
        export_format="excel",
        row_count=len(df)
    )
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={dataset.name}.xlsx"}
    )


@router.get("/csv/{dataset_id}")
async def export_to_csv(
    dataset_id: int,
    delimiter: Optional[str] = Query(","),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export dataset to CSV."""
    if not current_user.has_permission("export:csv"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSV export permission required"
        )
    
    dataset = await get_dataset_for_export(dataset_id, current_user, db)
    
    # Get data
    ingestion_service = FileIngestionService(db)
    df = ingestion_service.get_dataset_dataframe(dataset)
    
    # Create CSV
    output = io.StringIO()
    df.to_csv(output, sep=delimiter, index=False)
    output.seek(0)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_export(
        user=current_user,
        dataset_name=dataset.name,
        dataset_id=dataset.id,
        export_format="csv",
        row_count=len(df)
    )
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset.name}.csv"}
    )


@router.get("/json/{dataset_id}")
async def export_to_json(
    dataset_id: int,
    orient: Optional[str] = Query("records"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export dataset to JSON."""
    if not current_user.has_permission("export:json"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JSON export permission required"
        )
    
    dataset = await get_dataset_for_export(dataset_id, current_user, db)
    
    # Get data
    ingestion_service = FileIngestionService(db)
    df = ingestion_service.get_dataset_dataframe(dataset)
    
    # Create JSON
    json_data = df.to_json(orient=orient, indent=2)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_export(
        user=current_user,
        dataset_name=dataset.name,
        dataset_id=dataset.id,
        export_format="json",
        row_count=len(df)
    )
    
    return StreamingResponse(
        iter([json_data]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={dataset.name}.json"}
    )


@router.get("/parquet/{dataset_id}")
async def export_to_parquet(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export dataset to Parquet."""
    dataset = await get_dataset_for_export(dataset_id, current_user, db)
    
    # Get data
    ingestion_service = FileIngestionService(db)
    df = ingestion_service.get_dataset_dataframe(dataset)
    
    # Create Parquet file
    output = io.BytesIO()
    df.to_parquet(output, engine='pyarrow', index=False)
    output.seek(0)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_export(
        user=current_user,
        dataset_name=dataset.name,
        dataset_id=dataset.id,
        export_format="parquet",
        row_count=len(df)
    )
    
    return StreamingResponse(
        output,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={dataset.name}.parquet"}
    )
