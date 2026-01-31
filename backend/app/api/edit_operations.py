"""
Dataset Edit Operations API Routes

Handles edit sessions, locking, and data modifications.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User, Dataset
from app.core.rbac import get_current_user
from app.services.edit_session_service import EditSessionService


router = APIRouter()


# Pydantic Schemas
class LockRequest(BaseModel):
    timeout_minutes: int = Field(default=30, ge=1, le=120)


class LockResponse(BaseModel):
    session_id: str
    locked_at: str
    expires_at: str
    dataset_id: int
    user_id: int


class CellChange(BaseModel):
    row_index: int
    column_name: str
    old_value: Any = None
    new_value: Any


class CellUpdateRequest(BaseModel):
    session_id: str
    changes: List[CellChange]


class RowAddRequest(BaseModel):
    session_id: str
    position: int = Field(..., ge=0)
    data: Dict[str, Any]


class RowDeleteRequest(BaseModel):
    session_id: str
    row_indices: List[int]


class ColumnAddRequest(BaseModel):
    session_id: str
    name: str
    data_type: str = "string"
    default_value: Any = None


class ColumnDeleteRequest(BaseModel):
    session_id: str
    column_name: str


class SessionRequest(BaseModel):
    session_id: str


class ChangeResponse(BaseModel):
    id: int
    change_type: str
    row_index: Optional[int]
    column_name: Optional[str]
    old_value: Any
    new_value: Any
    timestamp: str
    is_committed: bool


# Edit Session Management
@router.post("/{dataset_id}/lock", response_model=LockResponse)
async def lock_dataset(
    dataset_id: int,
    lock_request: LockRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acquire an exclusive lock on a dataset for editing.
    
    Returns session_id and lock information.
    Raises 409 if dataset is already locked.
    """
    try:
        lock_info = EditSessionService.create_session(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id,
            timeout_minutes=lock_request.timeout_minutes
        )
        return LockResponse(**lock_info)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete("/{dataset_id}/lock")
async def unlock_dataset(
    dataset_id: int,
    session_request: SessionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Release an edit session lock."""
    released = EditSessionService.release_session(
        db=db,
        dataset_id=dataset_id,
        session_id=session_request.session_id
    )
    
    if not released:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lock not found or already released"
        )
    
    return {"message": "Lock released successfully"}


@router.get("/{dataset_id}/lock-status")
async def get_lock_status(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current lock status for a dataset."""
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    
    if lock_status is None:
        return {"locked": False}
    
    return {
        "locked": True,
        **lock_status
    }


@router.post("/{dataset_id}/lock/force-unlock")
async def force_unlock_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Force unlock a dataset (admin/owner only).
    Useful for clearing stale locks from crashed sessions.
    """
    # Get current lock status
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    
    if not lock_status:
        return {"message": "Dataset is not locked"}
    
    # Force release the lock
    released = EditSessionService.force_release_lock(db=db, dataset_id=dataset_id)
    
    if released:
        return {
            "message": "Lock forcefully released",
            "previous_session_id": lock_status.get("session_id"),
            "previous_user_id": lock_status.get("user_id")
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release lock"
        )


# Cell Operations
@router.post("/{dataset_id}/cells/update")
async def update_cells(
    dataset_id: int,
    update_request: CellUpdateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch update cells in a dataset.
    Logs all changes for audit trail.
    """
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != update_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Log each change
    logged_changes = []
    for change in update_request.changes:
        logged_change = EditSessionService.log_change(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id,
            session_id=update_request.session_id,
            change_type="cell_edit",
            row_index=change.row_index,
            column_name=change.column_name,
            old_value=change.old_value,
            new_value=change.new_value
        )
        logged_changes.append(logged_change)
    
    return {
        "message": f"Updated {len(logged_changes)} cells",
        "changes_logged": len(logged_changes)
    }


# Row Operations
@router.post("/{dataset_id}/rows")
async def add_row(
    dataset_id: int,
    row_request: RowAddRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new row to the dataset."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != row_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Log change
    logged_change = EditSessionService.log_change(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id,
        session_id=row_request.session_id,
        change_type="row_add",
        row_index=row_request.position,
        new_value=row_request.data
    )
    
    return {
        "message": "Row added successfully",
        "change_id": logged_change.id
    }


@router.delete("/{dataset_id}/rows")
async def delete_rows(
    dataset_id: int,
    delete_request: RowDeleteRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete rows from the dataset."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != delete_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Log each deletion
    logged_changes = []
    for row_idx in delete_request.row_indices:
        logged_change = EditSessionService.log_change(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id,
            session_id=delete_request.session_id,
            change_type="row_delete",
            row_index=row_idx
        )
        logged_changes.append(logged_change)
    
    return {
        "message": f"Deleted {len(logged_changes)} rows",
        "changes_logged": len(logged_changes)
    }


# Column Operations
@router.post("/{dataset_id}/columns")
async def add_column(
    dataset_id: int,
    column_request: ColumnAddRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new column to the dataset."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != column_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Log change
    logged_change = EditSessionService.log_change(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id,
        session_id=column_request.session_id,
        change_type="column_add",
        column_name=column_request.name,
        new_value={
            "data_type": column_request.data_type,
            "default_value": column_request.default_value
        }
    )
    
    return {
        "message": "Column added successfully",
        "change_id": logged_change.id
    }


@router.delete("/{dataset_id}/columns/{column_name}")
async def delete_column(
    dataset_id: int,
    column_name: str,
    session_request: SessionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a column from the dataset."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != session_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Log change
    logged_change = EditSessionService.log_change(
        db=db,
        dataset_id=dataset_id,
        user_id=current_user.id,
        session_id=session_request.session_id,
        change_type="column_delete",
        column_name=column_name
    )
    
    return {
        "message": "Column deleted successfully",
        "change_id": logged_change.id
    }


# Change Management
@router.post("/{dataset_id}/changes/commit")
async def commit_changes(
    dataset_id: int,
    session_request: SessionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Commit all changes in the current session."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != session_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Commit changes
    count = EditSessionService.commit_session(db=db, session_id=session_request.session_id)
    
    # Release lock
    EditSessionService.release_session(
        db=db,
        dataset_id=dataset_id,
        session_id=session_request.session_id
    )
    
    return {
        "message": "Changes committed successfully",
        "changes_committed": count
    }


@router.post("/{dataset_id}/changes/discard")
async def discard_changes(
    dataset_id: int,
    session_request: SessionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Discard all uncommitted changes in the current session."""
    # Verify lock
    lock_status = EditSessionService.get_lock_status(db=db, dataset_id=dataset_id)
    if not lock_status or lock_status["session_id"] != session_request.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired session"
        )
    
    # Rollback changes
    count = EditSessionService.rollback_session(db=db, session_id=session_request.session_id)
    
    # Release lock
    EditSessionService.release_session(
        db=db,
        dataset_id=dataset_id,
        session_id=session_request.session_id
    )
    
    return {
        "message": "Changes discarded successfully",
        "changes_discarded": count
    }


@router.get("/{dataset_id}/changes/history", response_model=List[ChangeResponse])
async def get_change_history(
    dataset_id: int,
    limit: int = 100,
    committed_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get change history for a dataset."""
    changes = EditSessionService.get_change_history(
        db=db,
        dataset_id=dataset_id,
        limit=limit,
        committed_only=committed_only
    )
    
    return [
        ChangeResponse(
            id=change.id,
            change_type=change.change_type,
            row_index=change.row_index,
            column_name=change.column_name,
            old_value=change.old_value,
            new_value=change.new_value,
            timestamp=change.timestamp.isoformat(),
            is_committed=change.is_committed
        )
        for change in changes
    ]


@router.get("/{dataset_id}/changes/uncommitted")
async def get_uncommitted_changes(
    dataset_id: int,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all uncommitted changes for the current session."""
    changes = EditSessionService.get_uncommitted_changes(db=db, session_id=session_id)
    
    return {
        "session_id": session_id,
        "count": len(changes),
        "changes": [
            {
                "id": change.id,
                "change_type": change.change_type,
                "row_index": change.row_index,
                "column_name": change.column_name,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "timestamp": change.timestamp.isoformat()
            }
            for change in changes
        ]
    }
