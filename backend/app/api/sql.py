"""
SQL Execution API Routes - DUAL DATABASE ARCHITECTURE
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import Connection, text
from typing import List, Optional
import time

from app.database import get_app_db, user_db_manager
from app.schemas import (
    SQLRequest, SQLResult, QueryExplainResult,
    SavedQuery, QueryHistoryItem, NoCodeQueryRequest, SQLResultColumn, QueryType
)
from app.models import User
from app.core.rbac import get_current_user
from app.core.audit import AuditLogger, QueryHistoryManager

router = APIRouter()


def execute_user_query(user_conn: Connection, query: str, limit: int = 1000) -> SQLResult:
    """
    Execute query on User Operational Database.
    
    SECURITY: This function ONLY executes on User DB, never on App DB.
    """
    start_time = time.time()
    
    try:
        # Detect query type
        query_stripped = query.strip().upper()
        is_select = query_stripped.startswith('SELECT')
        
        # Add limit for SELECT queries
        execution_query = query
        if is_select and 'LIMIT' not in query_stripped:
            execution_query = f"{query} LIMIT {limit}"
        
        # Execute query
        result = user_conn.execute(text(execution_query))
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        if is_select and result.returns_rows:
            # Fetch columns
            keys = result.keys()
            columns = [
                SQLResultColumn(name=key, data_type="unknown") 
                for key in keys
            ]
            
            # Fetch data
            rows = result.fetchall()
            data = [dict(zip(keys, row)) for row in rows]
            
            return SQLResult(
                success=True,
                query=query,
                query_type=QueryType.SELECT,
                columns=columns,
                data=data,
                row_count=len(data),
                execution_time_ms=execution_time_ms
            )
        else:
            # Non-SELECT (INSERT/UPDATE/DELETE)
            user_conn.commit()
            return SQLResult(
                success=True,
                query=query,
                query_type=QueryType.INSERT if 'INSERT' in query_stripped else QueryType.UPDATE,
                rows_affected=result.rowcount,
                execution_time_ms=execution_time_ms
            )
    
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return SQLResult(
            success=False,
            query=query,
            query_type=QueryType.SELECT,
            execution_time_ms=execution_time_ms,
            error_message=str(e)
        )


@router.post("/execute", response_model=SQLResult)
async def execute_sql(
    request: SQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
    app_db: Session = Depends(get_app_db)
):
    """
    Execute a SQL query on the User Operational Database.
    
    SECURITY: This endpoint ONLY executes queries on the User DB.
    App DB is used solely for audit logging and query history.
    """
    # Check permission
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    # Get User DB connection
    try:
        with user_db_manager.get_connection(app_db) as user_conn:
            # Execute query on User DB
            result = execute_user_query(user_conn, request.query, request.limit)
            
            # Audit log to App DB
            auditor = AuditLogger(app_db)
            auditor.log_query(
                user=current_user,
                query=request.query,
                duration_ms=result.execution_time_ms,
                rows_affected=result.rows_affected or result.row_count,
                success=result.success,
                error=result.error_message
            )
            
            # Record in query history (App DB)
            if result.success:
                history_manager = QueryHistoryManager(app_db)
                history_manager.record_query(
                    user_id=current_user.id,
                    query=request.query,
                    duration_ms=result.execution_time_ms
                )
            
            return result
    
    except ValueError as e:
        # No active connection configured
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.post("/explain", response_model=QueryExplainResult)
async def explain_query(
    request: SQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
    app_db: Session = Depends(get_app_db)
):
    """Get query execution plan from User DB."""
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    try:
        with user_db_manager.get_connection(app_db) as user_conn:
            explain_query = f"EXPLAIN {request.query}"
            result = user_conn.execute(text(explain_query))
            plan_text = "\n".join(str(row[0]) for row in result.fetchall())
            
            return QueryExplainResult(
                query=request.query,
                plan={"plan_text": plan_text},
                recommendations=[]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain query: {str(e)}"
        )


@router.post("/no-code", response_model=SQLResult)
async def execute_no_code_query(
    request: NoCodeQueryRequest = Body(...),
    current_user: User = Depends(get_current_user),
    app_db: Session = Depends(get_app_db)
):
    """Execute a no-code query builder request on User DB."""
    if not current_user.has_permission("sql:execute"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SQL execution permission required"
        )
    
    # Build query from no-code request
    # (Simplified - you may want to import NoCodeQueryBuilder from services)
    query = f"SELECT * FROM {request.datasets[0]}"
    if request.limit:
        query += f" LIMIT {request.limit}"
    
    try:
        with user_db_manager.get_connection(app_db) as user_conn:
            result = execute_user_query(user_conn, query, request.limit or 1000)
            
            # Audit log
            auditor = AuditLogger(app_db)
            auditor.log(
                action="no_code_query",
                user=current_user,
                resource_type="sql",
                details={"datasets": request.datasets}
            )
            
            return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    limit: int = Query(50, le=200),
    saved_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    app_db: Session = Depends(get_app_db)
):
    """Get user's query history from App DB."""
    history_manager = QueryHistoryManager(app_db)
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
    app_db: Session = Depends(get_app_db)
):
    """Save a query with a name in App DB."""
    history_manager = QueryHistoryManager(app_db)
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
    app_db: Session = Depends(get_app_db)
):
    """Toggle favorite status of a query in App DB."""
    history_manager = QueryHistoryManager(app_db)
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
    app_db: Session = Depends(get_app_db)
):
    """
    List all available tables in User Operational Database.
    
    SECURITY: This lists tables from User DB only, never App DB.
    """
    try:
        with user_db_manager.get_connection(app_db) as user_conn:
            # PostgreSQL-specific query for listing tables
            result = user_conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            return tables
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tables: {str(e)}"
        )
