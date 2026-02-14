"""
Models Package - Export all SQLAlchemy models
"""
from app.models.user import User, Role, Permission, RefreshToken
from app.models.dataset import Dataset, DatasetColumn, DatasetVersion, DatasetPermission, DatasetStatus, ColumnType
from app.models.dataset_change import DatasetChange
from app.models.dataset_lock import DatasetLock
from app.models.import_job import ImportJob, ImportMapping, ImportAuditLog
from app.models.audit import AuditLog, QueryHistory, TableEntryAudit, AuditActionType
from app.models.ai_config import AIConfig
from app.models.connection import (
    ConnectionProfile,
    ConnectionType,
    ConnectionGroup,
    ConnectionMode,
    HealthStatus
)
from app.models.connection_health import ConnectionHealthLog
from app.models.connection_permission import ConnectionPermission
from app.models.job import (
    ScheduledJob,
    JobExecution,
    JobParameter,
    JobType,
    JobStatus,
    BackupConfiguration,
    BackupType
)

__all__ = [
    # User & Auth
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    
    # Datasets
    "Dataset",
    "DatasetColumn",
    "DatasetVersion",
    "DatasetPermission",
    "DatasetStatus",
    "ColumnType",
    "DatasetChange",
    "DatasetLock",
    
    # Import
    "ImportJob",
    "ImportMapping",
    "ImportAuditLog",
    
    # Audit
    "AuditLog",
    "AuditActionType",
    "QueryHistory",
    "TableEntryAudit",
    
    # AI
    "AIConfig",
    
    # Connections
    "ConnectionProfile",
    "ConnectionType",
    "ConnectionGroup",
    "ConnectionMode",
    "HealthStatus",
    "ConnectionHealthLog",
    "ConnectionPermission",
    
    # Jobs
    "ScheduledJob",
    "JobExecution",
    "JobParameter",
    "JobType",
    "JobStatus",
    "BackupConfiguration",
    "BackupType",
]
