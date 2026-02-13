"""
Base Job Executor
Abstract base class for all job executors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()


@dataclass
class ValidationResult:
    """Result of job configuration validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class ExecutionResult:
    """Result of job execution"""
    success: bool
    rows_processed: int = 0
    rows_affected: int = 0
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_stack_trace: Optional[str] = None
    execution_logs: str = ""
    resource_usage: Optional[Dict[str, Any]] = None


class JobExecutorBase(ABC):
    """Base class for all job executors"""
    
    def __init__(self, connection_string: str, job_config: Dict[str, Any]):
        """
        Initialize executor
        
        Args:
            connection_string: Database connection string
            job_config: Job-specific configuration
        """
        self.connection_string = connection_string
        self.job_config = job_config
        self.logger = logger.bind(executor=self.__class__.__name__)
        self._logs = []
    
    def log(self, message: str, level: str = "info", **kwargs):
        """Add log entry"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        if kwargs:
            log_entry += f" {kwargs}"
        self._logs.append(log_entry)
        
        # Also log to structlog
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message, **kwargs)
    
    def get_logs(self) -> str:
        """Get accumulated logs as string"""
        return "\n".join(self._logs)
    
    @abstractmethod
    def validate_config(self) -> ValidationResult:
        """
        Validate job configuration
        
        Returns:
            ValidationResult with validation status and messages
        """
        pass
    
    @abstractmethod
    def execute(self, execution_id: int) -> ExecutionResult:
        """
        Execute the job
        
        Args:
            execution_id: ID of the job execution record
            
        Returns:
            ExecutionResult with execution status and results
        """
        pass
    
    @abstractmethod
    def get_required_permissions(self) -> List[str]:
        """
        Get list of required database permissions
        
        Returns:
            List of permission names
        """
        pass
    
    def cleanup(self):
        """Cleanup resources after execution"""
        pass
    
    def _sanitize_for_logging(self, data: Any) -> Any:
        """Sanitize sensitive data for logging"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'token', 'key']):
                    sanitized[key] = "***REDACTED***"
                else:
                    sanitized[key] = self._sanitize_for_logging(value)
            return sanitized
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_for_logging(item) for item in data]
        return data
