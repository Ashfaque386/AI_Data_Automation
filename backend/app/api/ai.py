"""
AI API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List

from app.database import get_db
from app.models import User, Dataset
from app.core.rbac import get_current_user, DatasetAccessChecker
from app.services.ai_service import AIService
from app.services.sql_engine import SQLEngine

router = APIRouter()


class NLToSQLRequest(BaseModel):
    query: str
    dataset_ids: List[int] = []
    model: str = None


class FormulaSuggestionRequest(BaseModel):
    description: str
    dataset_id: int
    model: str = None


class QualityCheckRequest(BaseModel):
    dataset_id: int
    model: str = None


@router.get("/models")
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """Get list of available AI models."""
    ai_service = AIService()
    models = await ai_service.get_available_models()
    return {"models": models}


@router.post("/nl-to-sql")
async def natural_language_to_sql(
    request: NLToSQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert natural language to SQL query."""
    ai_service = AIService()
    sql_engine = SQLEngine(db)
    
    # Get table schemas
    tables_schema = {}
    
    if request.dataset_ids:
        for dataset_id in request.dataset_ids:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset and DatasetAccessChecker.can_read(db, current_user, dataset):
                schema = sql_engine.get_table_schema(dataset.virtual_table_name)
                tables_schema[dataset.virtual_table_name] = schema
    else:
        # Get all accessible tables
        tables = sql_engine.list_tables()
        for table in tables:
            schema = sql_engine.get_table_schema(table)
            tables_schema[table] = schema
    
    try:
        sql_query = await ai_service.natural_language_to_sql(
            request.query,
            tables_schema,
            model=request.model
        )
        return {
            "success": True,
            "sql": sql_query,
            "tables_used": list(tables_schema.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-formula")
async def suggest_formula(
    request: FormulaSuggestionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Suggest Excel formula based on description."""
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if not DatasetAccessChecker.can_read(db, current_user, dataset):
        raise HTTPException(status_code=403, detail="No access to this dataset")
    
    column_names = [col.name for col in dataset.columns]
    
    ai_service = AIService()
    try:
        formula = await ai_service.suggest_formula(
            request.description,
            column_names,
            model=request.model
        )
        return {
            "success": True,
            "formula": formula
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality-check")
async def check_data_quality(
    request: QualityCheckRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check data quality using AI."""
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if not DatasetAccessChecker.can_read(db, current_user, dataset):
        raise HTTPException(status_code=403, detail="No access to this dataset")
    
    # Build dataset summary
    summary = {
        "name": dataset.name,
        "row_count": dataset.row_count,
        "columns": [
            {
                "name": col.name,
                "type": col.data_type,
                "nullable": col.nullable,
                "unique_count": col.unique_count,
                "null_count": col.null_count,
                "sample_values": col.sample_values
            }
            for col in dataset.columns
        ]
    }
    
    ai_service = AIService()
    try:
        issues = await ai_service.detect_data_quality_issues(summary, model=request.model)
        return {
            "success": True,
            "issues": issues,
            "total_issues": len(issues)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
