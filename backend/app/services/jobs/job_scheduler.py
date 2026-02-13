"""
Job Scheduler
Manages cron-based job scheduling and execution timing
"""
from typing import List, Optional, Tuple, Any
from datetime import datetime, timedelta
from croniter import croniter
import pytz
import structlog

logger = structlog.get_logger()


class JobScheduler:
    """Cron-based job scheduler"""
    
    @staticmethod
    def validate_cron_expression(cron_expression: str) -> tuple[bool, Optional[str]]:
        """
        Validate a cron expression
        
        Args:
            cron_expression: Cron expression string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            croniter(cron_expression)
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def calculate_next_run(cron_expression: str, timezone: str = 'UTC', base_time: Optional[datetime] = None) -> datetime:
        """
        Calculate next run time from cron expression
        
        Args:
            cron_expression: Cron expression string
            timezone: Timezone name (e.g., 'UTC', 'America/New_York')
            base_time: Base time for calculation (defaults to now)
            
        Returns:
            Next run datetime in UTC
        """
        try:
            # Get timezone
            tz = pytz.timezone(timezone)
            
            # Get base time in specified timezone
            if base_time is None:
                base_time = datetime.now(tz)
            elif base_time.tzinfo is None:
                base_time = tz.localize(base_time)
            else:
                base_time = base_time.astimezone(tz)
            
            # Calculate next run
            cron = croniter(cron_expression, base_time)
            next_run = cron.get_next(datetime)
            
            # Convert to UTC
            next_run_utc = next_run.astimezone(pytz.UTC)
            
            logger.debug("calculated_next_run",
                        cron_expression=cron_expression,
                        timezone=timezone,
                        next_run=next_run_utc.isoformat())
            
            return next_run_utc  # Return aware UTC datetime
            
        except Exception as e:
            logger.error("next_run_calculation_failed",
                        cron_expression=cron_expression,
                        error=str(e))
            raise
    
    @staticmethod
    def calculate_next_n_runs(cron_expression: str, n: int = 5, timezone: str = 'UTC') -> List[datetime]:
        """
        Calculate next N run times
        
        Args:
            cron_expression: Cron expression string
            n: Number of runs to calculate
            timezone: Timezone name
            
        Returns:
            List of next N run datetimes in UTC
        """
        try:
            tz = pytz.timezone(timezone)
            base_time = datetime.now(tz)
            
            cron = croniter(cron_expression, base_time)
            next_runs = []
            
            for _ in range(n):
                next_run = cron.get_next(datetime)
                next_run_utc = next_run.astimezone(pytz.UTC)
                next_runs.append(next_run_utc)
            
            return next_runs
            
        except Exception as e:
            logger.error("next_runs_calculation_failed",
                        cron_expression=cron_expression,
                        error=str(e))
            raise
    
    @staticmethod
    def is_due(job: Any, current_time: Optional[datetime] = None) -> bool:
        """
        Check if a job is due to run
        
        Args:
            job: ScheduledJob instance
            current_time: Current time (defaults to now)
            
        Returns:
            True if job should run now
        """
        if not job.is_active:
            return False
        
        if not job.cron_expression:
            return False
        
        if current_time is None:
            current_time = datetime.now(pytz.UTC)
        
        # Check if next_run_at is in the past
        if job.next_run_at and job.next_run_at <= current_time:
            return True
        
        return False
    
    @staticmethod
    def update_next_run(job: Any, db_session: Any):
        """
        Update job's next run time
        
        Args:
            job: ScheduledJob instance
            db_session: Database session
        """
        if not job.cron_expression:
            job.next_run_at = None
            db_session.commit()
            return
        
        try:
            next_run = JobScheduler.calculate_next_run(
                job.cron_expression,
                job.timezone or 'UTC'
            )
            job.next_run_at = next_run
            db_session.commit()
            
            logger.info("next_run_updated",
                       job_id=job.id,
                       next_run=next_run.isoformat())
            
        except Exception as e:
            logger.error("next_run_update_failed",
                        job_id=job.id,
                        error=str(e))
    
    @staticmethod
    def get_preset_cron(preset: str) -> Optional[str]:
        """
        Get cron expression for common presets
        
        Args:
            preset: Preset name
            
        Returns:
            Cron expression or None
        """
        presets = {
            'hourly': '0 * * * *',
            'daily': '0 0 * * *',
            'daily_2am': '0 2 * * *',
            'weekly': '0 0 * * 0',
            'weekly_monday': '0 0 * * 1',
            'monthly': '0 0 1 * *',
            'every_5_minutes': '*/5 * * * *',
            'every_15_minutes': '*/15 * * * *',
            'every_30_minutes': '*/30 * * * *',
        }
        
        return presets.get(preset.lower())
