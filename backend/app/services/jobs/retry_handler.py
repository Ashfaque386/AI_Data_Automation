"""
Retry Handler
Implements retry logic with exponential backoff for failed jobs
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import time
import structlog

logger = structlog.get_logger()


class RetryHandler:
    """Handle job retry logic with exponential backoff"""
    
    @staticmethod
    def should_retry(job: Any, execution: Any) -> bool:
        """
        Determine if a failed job should be retried
        
        Args:
            job: ScheduledJob instance
            execution: JobExecution instance
            
        Returns:
            True if job should be retried
        """
        # Get retry policy from job config
        retry_policy = job.retry_policy or {}
        max_retries = retry_policy.get('max_retries', 3)
        
        # Check if we've exceeded max retries
        if execution.retry_count >= max_retries:
            logger.info("max_retries_exceeded", 
                       job_id=job.id, 
                       retry_count=execution.retry_count,
                       max_retries=max_retries)
            return False
        
        # Check if job is still active
        if not job.is_active:
            logger.info("job_inactive_no_retry", job_id=job.id)
            return False
        
        # Check failure threshold
        if job.consecutive_failures >= job.failure_threshold:
            logger.warning("failure_threshold_exceeded",
                          job_id=job.id,
                          consecutive_failures=job.consecutive_failures,
                          threshold=job.failure_threshold)
            return False
        
        return True
    
    @staticmethod
    def calculate_backoff_delay(retry_count: int, retry_policy: Optional[Dict[str, Any]] = None) -> int:
        """
        Calculate delay before next retry using exponential backoff
        
        Args:
            retry_count: Current retry attempt number (0-indexed)
            retry_policy: Retry policy configuration
            
        Returns:
            Delay in seconds
        """
        retry_policy = retry_policy or {}
        
        base_delay = retry_policy.get('base_delay_seconds', 60)  # 1 minute default
        backoff_multiplier = retry_policy.get('backoff_multiplier', 2)
        max_backoff = retry_policy.get('max_backoff_seconds', 3600)  # 1 hour max
        
        # Calculate exponential backoff: base_delay * (multiplier ^ retry_count)
        delay = base_delay * (backoff_multiplier ** retry_count)
        
        # Cap at max backoff
        delay = min(delay, max_backoff)
        
        logger.info("calculated_backoff_delay",
                   retry_count=retry_count,
                   delay_seconds=delay)
        
        return int(delay)
    
    @staticmethod
    def calculate_next_retry_time(retry_count: int, retry_policy: Optional[Dict[str, Any]] = None) -> datetime:
        """
        Calculate when the next retry should occur
        
        Args:
            retry_count: Current retry attempt number
            retry_policy: Retry policy configuration
            
        Returns:
            Datetime for next retry
        """
        delay_seconds = RetryHandler.calculate_backoff_delay(retry_count, retry_policy)
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        logger.info("next_retry_scheduled",
                   retry_count=retry_count,
                   delay_seconds=delay_seconds,
                   next_retry=next_retry.isoformat())
        
        return next_retry
    
    @staticmethod
    def reset_retry_state(job: Any, db_session: Any):
        """
        Reset retry state after successful execution
        
        Args:
            job: ScheduledJob instance
            db_session: Database session
        """
        job.consecutive_failures = 0
        db_session.commit()
        
        logger.info("retry_state_reset", job_id=job.id)
    
    @staticmethod
    def increment_failure_count(job: Any, db_session: Any):
        """
        Increment failure counters
        
        Args:
            job: ScheduledJob instance
            db_session: Database session
        """
        job.failure_count += 1
        job.consecutive_failures += 1
        
        # Auto-disable if threshold exceeded
        if job.consecutive_failures >= job.failure_threshold:
            job.is_active = False
            logger.warning("job_auto_disabled",
                          job_id=job.id,
                          consecutive_failures=job.consecutive_failures,
                          threshold=job.failure_threshold)
        
        db_session.commit()
