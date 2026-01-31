"""
Edit Session Service

Manages dataset edit sessions, locking, and change tracking.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.dataset import Dataset
from app.models.dataset_lock import DatasetLock
from app.models.dataset_change import DatasetChange


class EditSessionService:
    """Service for managing dataset edit sessions and change tracking."""
    
    @staticmethod
    def create_session(
        db: Session,
        dataset_id: int,
        user_id: int,
        timeout_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Create a new edit session and lock the dataset.
        
        Args:
            db: Database session
            dataset_id: ID of dataset to lock
            user_id: ID of user creating the session
            timeout_minutes: Lock timeout in minutes (default 30)
            
        Returns:
            Dict with session_id and lock info
            
        Raises:
            ValueError: If dataset is already locked
        """
        # Check if dataset exists
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Check for existing lock
        existing_lock = db.query(DatasetLock).filter(
            DatasetLock.dataset_id == dataset_id
        ).first()
        
        if existing_lock:
            # Check if lock is expired
            if not existing_lock.is_expired:
                raise ValueError(
                    f"Dataset is locked by user {existing_lock.user_id} "
                    f"until {existing_lock.expires_at}"
                )
            # Remove expired lock
            db.delete(existing_lock)
            db.commit()
        
        # Create new lock
        session_id = str(uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
        
        lock = DatasetLock(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            expires_at=expires_at
        )
        
        db.add(lock)
        db.commit()
        db.refresh(lock)
        
        return {
            "session_id": session_id,
            "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
            "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
            "dataset_id": dataset_id,
            "user_id": user_id
        }
    
    @staticmethod
    def release_session(db: Session, dataset_id: int, session_id: str) -> bool:
        """
        Release an edit session lock.
        
        Args:
            db: Database session
            dataset_id: ID of locked dataset
            session_id: Session ID to release
            
        Returns:
            True if lock was released, False if not found
        """
        lock = db.query(DatasetLock).filter(
            and_(
                DatasetLock.dataset_id == dataset_id,
                DatasetLock.session_id == session_id
            )
        ).first()
        
        if lock:
            db.delete(lock)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_lock_status(db: Session, dataset_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current lock status for a dataset.
        
        Args:
            db: Database session
            dataset_id: ID of dataset
            
        Returns:
            Lock info dict or None if unlocked
        """
        lock = db.query(DatasetLock).filter(
            DatasetLock.dataset_id == dataset_id
        ).first()
        
        if not lock:
            return None
        
        # Check if expired
        if lock.is_expired:
            db.delete(lock)
            db.commit()
            return None
        
        return {
            "dataset_id": lock.dataset_id,
            "user_id": lock.user_id,
            "session_id": lock.session_id,
            "locked_at": lock.locked_at.isoformat() if lock.locked_at else None,
            "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
            "is_expired": lock.is_expired
        }
    
    @staticmethod
    def force_release_lock(db: Session, dataset_id: int) -> bool:
        """
        Force release any lock on a dataset, regardless of session or user.
        Useful for clearing stale locks.
        
        Args:
            db: Database session
            dataset_id: ID of dataset to unlock
            
        Returns:
            True if lock was released, False if no lock existed
        """
        lock = db.query(DatasetLock).filter(
            DatasetLock.dataset_id == dataset_id
        ).first()
        
        if lock:
            db.delete(lock)
            db.commit()
            return True
        return False
    
    @staticmethod
    def log_change(
        db: Session,
        dataset_id: int,
        user_id: int,
        session_id: str,
        change_type: str,
        row_index: Optional[int] = None,
        column_name: Optional[str] = None,
        old_value: Any = None,
        new_value: Any = None
    ) -> DatasetChange:
        """
        Log a change to the dataset.
        
        Args:
            db: Database session
            dataset_id: ID of dataset
            user_id: ID of user making change
            session_id: Current edit session ID
            change_type: Type of change (cell_edit, row_add, etc.)
            row_index: Row index for row operations
            column_name: Column name for cell/column operations
            old_value: Previous value
            new_value: New value
            
        Returns:
            Created DatasetChange object
        """
        change = DatasetChange(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            change_type=change_type,
            row_index=row_index,
            column_name=column_name,
            old_value=old_value,
            new_value=new_value,
            is_committed=False
        )
        
        db.add(change)
        db.commit()
        db.refresh(change)
        
        return change
    
    @staticmethod
    def get_uncommitted_changes(
        db: Session,
        session_id: str
    ) -> List[DatasetChange]:
        """
        Get all uncommitted changes for a session.
        
        Args:
            db: Database session
            session_id: Session ID
            
        Returns:
            List of DatasetChange objects
        """
        return db.query(DatasetChange).filter(
            and_(
                DatasetChange.session_id == session_id,
                DatasetChange.is_committed == False
            )
        ).order_by(DatasetChange.timestamp).all()
    
    @staticmethod
    def commit_session(db: Session, session_id: str) -> int:
        """
        Mark all changes in a session as committed.
        
        Args:
            db: Database session
            session_id: Session ID to commit
            
        Returns:
            Number of changes committed
        """
        result = db.query(DatasetChange).filter(
            and_(
                DatasetChange.session_id == session_id,
                DatasetChange.is_committed == False
            )
        ).update({"is_committed": True})
        
        db.commit()
        return result
    
    @staticmethod
    def rollback_session(db: Session, session_id: str) -> int:
        """
        Delete all uncommitted changes for a session.
        
        Args:
            db: Database session
            session_id: Session ID to rollback
            
        Returns:
            Number of changes deleted
        """
        changes = db.query(DatasetChange).filter(
            and_(
                DatasetChange.session_id == session_id,
                DatasetChange.is_committed == False
            )
        ).all()
        
        count = len(changes)
        for change in changes:
            db.delete(change)
        
        db.commit()
        return count
    
    @staticmethod
    def get_change_history(
        db: Session,
        dataset_id: int,
        limit: int = 100,
        committed_only: bool = True
    ) -> List[DatasetChange]:
        """
        Get change history for a dataset.
        
        Args:
            db: Database session
            dataset_id: ID of dataset
            limit: Maximum number of changes to return
            committed_only: If True, only return committed changes
            
        Returns:
            List of DatasetChange objects
        """
        query = db.query(DatasetChange).filter(
            DatasetChange.dataset_id == dataset_id
        )
        
        if committed_only:
            query = query.filter(DatasetChange.is_committed == True)
        
        return query.order_by(
            DatasetChange.timestamp.desc()
        ).limit(limit).all()
