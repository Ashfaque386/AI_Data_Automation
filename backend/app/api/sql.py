"""
SQL Execution API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas import (
    SQLRequest, SQLResult, QueryExplainResult,
    SavedQuery, QueryHistoryItem, NoCodeQueryRequest
)
from app.models import User
from app.core.rbac import get_current_user
from app.core.audit import AuditLogger, QueryHistoryManager
from app.services import SQLEngine
import time

router = APIRouter()


@router.post("/execute", response_model=SQLResult)
async def execute_sql(
    request: SQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a SQL query."""
    # Check permission
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    # Execute query
    sql_engine = SQLEngine(db)
    start_time = time.time()
    result = sql_engine.execute(
        query=request.query,
        limit=request.limit,
        timeout_seconds=request.timeout_seconds,
        source=request.source
    )
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log_query(
        user=current_user,
        query=request.query,
        duration_ms=duration_ms,
        rows_affected=result.rows_affected or result.row_count,
        success=result.success,
        error=result.error_message
    )
    
    # Record in query history
    if result.success:
        history_manager = QueryHistoryManager(db)
        history_manager.record_query(
            user_id=current_user.id,
            query=request.query,
            duration_ms=duration_ms
        )
    
    return result


@router.post("/explain", response_model=QueryExplainResult)
async def explain_query(
    request: SQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query execution plan."""
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    sql_engine = SQLEngine(db)
    result = sql_engine.explain(request.query)
    
    return result


@router.post("/no-code", response_model=SQLResult)
async def execute_no_code_query(
    request: NoCodeQueryRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a no-code query builder request."""
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    sql_engine = SQLEngine(db)
    result = sql_engine.execute_no_code(request)
    
    # Audit log
    auditor = AuditLogger(db)
    auditor.log(
        action="no_code_query",
        user=current_user,
        resource_type="sql",
        details={"datasets": request.datasets, "filters": len(request.filters)}
    )
    
    return result


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    limit: int = Query(50, le=200),
    saved_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's query history."""
    history_manager = QueryHistoryManager(db)
    history = history_manager.get_user_history(
        user_id=current_user.id,
        limit=limit,
        saved_only=saved_only
    )
    
    return history


@router.post("/history/{query_id}/save")
async def save_query(
    query_id: int,
    query_data: SavedQuery = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a query with a name."""
    history_manager = QueryHistoryManager(db)
    query = history_manager.save_query(
        user_id=current_user.id,
        query_id=query_id,
        name=query_data.name
    )
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    return {"message": "Query saved successfully", "id": query.id}


@router.post("/history/{query_id}/favorite")
async def toggle_favorite(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle favorite status of a query."""
    history_manager = QueryHistoryManager(db)
    query = history_manager.toggle_favorite(
        user_id=current_user.id,
        query_id=query_id
    )
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    return {"message": "Favorite toggled", "is_favorite": query.is_favorite}


@router.get("/tables", response_model=List[str])
async def list_tables(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available tables."""
    sql_engine = SQLEngine(db)
    tables = sql_engine.list_tables()
    
    return tables
