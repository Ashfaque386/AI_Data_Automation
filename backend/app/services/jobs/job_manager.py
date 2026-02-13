"""
Job Manager
Central service for job lifecycle management
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import structlog
import traceback

from app.models import ScheduledJob, JobExecution, JobStatus, JobType, ConnectionProfile, User
from app.services.jobs.sql_script_executor import SQLScriptExecutor
from app.services.jobs.procedure_executor import ProcedureExecutor
from app.services.jobs.backup_executor import BackupExecutor
from app.services.jobs.job_scheduler import JobScheduler
from app.services.jobs.retry_handler import RetryHandler
from app.core.crypto import decrypt_value

logger = structlog.get_logger()


class JobManager:
    """Manage job lifecycle and execution"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.logger = logger.bind(service="JobManager")
    
    def create_job(self, job_data: Dict[str, Any], user_id: int) -> ScheduledJob:
        """
        Create a new scheduled job
        
        Args:
            job_data: Job configuration data
            user_id: ID of user creating the job
            
        Returns:
            Created ScheduledJob instance
        """
        self.logger.info("creating_job", job_type=job_data.get('job_type'), user_id=user_id)
        
        # Validate cron expression if provided
        if job_data.get('cron_expression'):
            is_valid, error = JobScheduler.validate_cron_expression(job_data['cron_expression'])
            if not is_valid:
                raise ValueError(f"Invalid cron expression: {error}")
        
        # Create job
        job = ScheduledJob(
            name=job_data['name'],
            description=job_data.get('description'),
            job_type=job_data['job_type'],
            connection_id=job_data.get('connection_id'),
            target_schema=job_data.get('target_schema'),
            cron_expression=job_data.get('cron_expression'),
            timezone=job_data.get('timezone', 'UTC'),
            is_active=job_data.get('is_active', True),
            config=job_data['config'],
            pre_execution_sql=job_data.get('pre_execution_sql'),
            post_execution_sql=job_data.get('post_execution_sql'),
            retry_policy=job_data.get('retry_policy'),
            max_runtime_seconds=job_data.get('max_runtime_seconds', 3600),
            failure_threshold=job_data.get('failure_threshold', 5),
            notify_on_success=job_data.get('notify_on_success', False),
            notify_on_failure=job_data.get('notify_on_failure', True),
            notification_emails=job_data.get('notification_emails'),
            notification_webhook=job_data.get('notification_webhook'),
            created_by_id=user_id
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Calculate next run time if cron expression provided
        if job.cron_expression:
            JobScheduler.update_next_run(job, self.db)
        
        self.logger.info("job_created", job_id=job.id, job_name=job.name)
        
        return job
    
    def execute_job(self, job_id: int, user_id: Optional[int] = None, triggered_by: str = 'manual') -> JobExecution:
        """
        Execute a job
        
        Args:
            job_id: ID of job to execute
            user_id: ID of user triggering execution (optional)
            triggered_by: Trigger source ('manual', 'schedule', 'api')
            
        Returns:
            JobExecution instance
        """
        self.logger.info("executing_job", job_id=job_id, triggered_by=triggered_by)
        
        # Get job
        job = self.db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        # Only scheduled executions require the job to be active
        # Manual executions (including quick backups) can run even if inactive
        if not job.is_active and triggered_by == 'schedule':
            raise ValueError(f"Job is not active: {job_id}")
        
        # Create execution record
        execution = JobExecution(
            job_id=job.id,
            status=JobStatus.PENDING.value,
            triggered_by=triggered_by,
            triggered_by_user_id=user_id
        )
        
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        # Update execution status to running
        execution.status = JobStatus.RUNNING.value
        execution.started_at = datetime.now(timezone.utc)
        self.db.commit()
        
        try:
            # Get connection string
            connection_string = self._get_connection_string(job.connection_id)
            
            # Execute pre-execution SQL if provided
            if job.pre_execution_sql:
                self.logger.info("executing_pre_sql", job_id=job.id)
                # TODO: Execute pre-execution SQL
            
            # Execute job based on type
            executor = self._get_executor(job, connection_string)
            result = executor.execute(execution.id)
            
            # Execute post-execution SQL if provided
            if job.post_execution_sql and result.success:
                self.logger.info("executing_post_sql", job_id=job.id)
                # TODO: Execute post-execution SQL
            
            # Update execution record
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            execution.status = JobStatus.COMPLETED.value if result.success else JobStatus.FAILED.value
            execution.rows_processed = result.rows_processed
            execution.rows_affected = result.rows_affected
            execution.result = result.result_data
            execution.error_message = result.error_message
            execution.error_stack_trace = result.error_stack_trace
            execution.execution_logs = result.execution_logs
            execution.resource_usage = result.resource_usage
            
            # Update job statistics
            job.last_run_at = execution.completed_at
            job.run_count += 1
            
            if result.success:
                job.success_count += 1
                RetryHandler.reset_retry_state(job, self.db)
            else:
                RetryHandler.increment_failure_count(job, self.db)
                
                # Check if should retry
                if RetryHandler.should_retry(job, execution):
                    self.logger.info("scheduling_retry", job_id=job.id, execution_id=execution.id)
                    # TODO: Schedule retry
            
            # Update next run time if scheduled
            if job.cron_expression:
                JobScheduler.update_next_run(job, self.db)
            
            self.db.commit()
            
            self.logger.info("job_execution_completed",
                           job_id=job.id,
                           execution_id=execution.id,
                           success=result.success)
            
            return execution
            
        except Exception as e:
            self.logger.error("job_execution_failed",
                            job_id=job.id,
                            execution_id=execution.id,
                            error=str(e))
            
            # Update execution as failed
            execution.status = JobStatus.FAILED.value
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            execution.error_message = str(e)
            
            # Update job statistics
            job.last_run_at = execution.completed_at
            job.run_count += 1
            RetryHandler.increment_failure_count(job, self.db)
            
            self.db.commit()
            
            raise
    
    def cancel_execution(self, execution_id: int) -> bool:
        """
        Cancel a running job execution
        
        Args:
            execution_id: ID of execution to cancel
            
        Returns:
            True if cancelled successfully
        """
        execution = self.db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if execution.status != JobStatus.RUNNING.value:
            raise ValueError(f"Execution is not running: {execution_id}")
        
        # Update status
        execution.status = JobStatus.CANCELLED.value
        execution.completed_at = datetime.now(timezone.utc)
        if execution.started_at:
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
        
        self.db.commit()
        
        self.logger.info("execution_cancelled", execution_id=execution_id)
        
        return True
    
    def _get_connection_string(self, connection_id: int) -> str:
        """Get connection string for a connection profile"""
        connection = self.db.query(ConnectionProfile).filter(
            ConnectionProfile.id == connection_id
        ).first()
        
        if not connection:
            raise ValueError(f"Connection not found: {connection_id}")
        
        # Decrypt password
        password = decrypt_value(connection.encrypted_password) if connection.encrypted_password else ""
        
        return connection.get_connection_string(password)
    
    def _get_executor(self, job: ScheduledJob, connection_string: str):
        """Get appropriate executor for job type"""
        if job.job_type == JobType.SQL_SCRIPT.value:
            return SQLScriptExecutor(connection_string, job.config)
        elif job.job_type == JobType.STORED_PROCEDURE.value:
            return ProcedureExecutor(connection_string, job.config)
        elif job.job_type == JobType.DATABASE_BACKUP.value:
            storage_path = job.config.get('storage_path', '/app/backups')
            return BackupExecutor(connection_string, job.config, storage_path)
        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")
