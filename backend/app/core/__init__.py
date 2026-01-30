"""
Core Package
"""
from app.core.auth import (
    create_access_token, create_refresh_token, create_tokens,
    verify_token, authenticate_user, refresh_access_token,
    get_user_by_id, get_user_by_email
)
from app.core.rbac import (
    get_current_user, get_current_active_user, get_current_superuser,
    require_permission, require_permissions,
    DatasetAccessChecker, PermissionDeniedError, UnauthorizedError,
    initialize_rbac, DEFAULT_PERMISSIONS, DEFAULT_ROLES
)
from app.core.audit import AuditLogger, QueryHistoryManager

__all__ = [
    # Auth
    "create_access_token", "create_refresh_token", "create_tokens",
    "verify_token", "authenticate_user", "refresh_access_token",
    "get_user_by_id", "get_user_by_email",
    # RBAC
    "get_current_user", "get_current_active_user", "get_current_superuser",
    "require_permission", "require_permissions",
    "DatasetAccessChecker", "PermissionDeniedError", "UnauthorizedError",
    "initialize_rbac", "DEFAULT_PERMISSIONS", "DEFAULT_ROLES",
    # Audit
    "AuditLogger", "QueryHistoryManager"
]
