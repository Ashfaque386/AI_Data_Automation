/**
 * Permissions Manager Component
 * Manage user permissions for a specific connection
 */
import React, { useState, useEffect } from 'react';
import { permissionsApi, ConnectionPermission, PermissionGrantRequest } from '../../services/permissionsApi';
import './PermissionsManager.css';

interface PermissionsManagerProps {
    connectionId: number;
    connectionName: string;
    onClose: () => void;
}

export const PermissionsManager: React.FC<PermissionsManagerProps> = ({
    connectionId,
    connectionName,
    onClose
}) => {
    const [permissions, setPermissions] = useState<ConnectionPermission[]>([]);
    const [loading, setLoading] = useState(true);
    const [newUserId, setNewUserId] = useState<string>('');
    const [canRead, setCanRead] = useState(true);
    const [canWrite, setCanWrite] = useState(false);
    const [canExecuteDDL, setCanExecuteDDL] = useState(false);
    const [allowedSchemas, setAllowedSchemas] = useState<string>('');
    const [deniedTables, setDeniedTables] = useState<string>('');

    useEffect(() => {
        loadPermissions();
    }, [connectionId]);

    const loadPermissions = async () => {
        try {
            setLoading(true);
            const data = await permissionsApi.listConnectionPermissions(connectionId);
            setPermissions(data);
        } catch (error) {
            console.error('Failed to load permissions:', error);
            alert('Failed to load permissions');
        } finally {
            setLoading(false);
        }
    };

    const handleGrantPermission = async () => {
        if (!newUserId) {
            alert('Please enter a user ID');
            return;
        }

        try {
            const request: PermissionGrantRequest = {
                user_id: parseInt(newUserId),
                can_read: canRead,
                can_write: canWrite,
                can_execute_ddl: canExecuteDDL,
                allowed_schemas: allowedSchemas ? allowedSchemas.split(',').map(s => s.trim()).filter(s => s) : undefined,
                denied_tables: deniedTables ? deniedTables.split(',').map(t => t.trim()).filter(t => t) : undefined
            };

            await permissionsApi.grantPermission(connectionId, request);

            // Reset form
            setNewUserId('');
            setCanRead(true);
            setCanWrite(false);
            setCanExecuteDDL(false);
            setAllowedSchemas('');
            setDeniedTables('');

            // Reload permissions
            await loadPermissions();

            alert('Permission granted successfully');
        } catch (error: any) {
            console.error('Failed to grant permission:', error);
            alert(error.response?.data?.detail || 'Failed to grant permission');
        }
    };

    const handleRevokePermission = async (userId: number) => {
        if (!confirm('Are you sure you want to revoke all permissions for this user?')) {
            return;
        }

        try {
            await permissionsApi.revokePermission(connectionId, userId);
            await loadPermissions();
            alert('Permission revoked successfully');
        } catch (error) {
            console.error('Failed to revoke permission:', error);
            alert('Failed to revoke permission');
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content permissions-manager" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>🔐 Manage Permissions</h2>
                    <p className="subtitle">Connection: {connectionName}</p>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {/* Grant Permission Form */}
                    <div className="grant-permission-section">
                        <h3>Grant Permission</h3>
                        <div className="form-grid">
                            <div className="form-group">
                                <label>User ID</label>
                                <input
                                    type="number"
                                    value={newUserId}
                                    onChange={(e) => setNewUserId(e.target.value)}
                                    placeholder="Enter user ID"
                                />
                            </div>
                        </div>

                        <div className="permissions-checkboxes">
                            <label className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={canRead}
                                    onChange={(e) => setCanRead(e.target.checked)}
                                />
                                <span>Read (SELECT queries)</span>
                            </label>
                            <label className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={canWrite}
                                    onChange={(e) => setCanWrite(e.target.checked)}
                                />
                                <span>Write (INSERT, UPDATE, DELETE)</span>
                            </label>
                            <label className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={canExecuteDDL}
                                    onChange={(e) => setCanExecuteDDL(e.target.checked)}
                                />
                                <span>Execute DDL (CREATE, DROP, ALTER)</span>
                            </label>
                        </div>

                        <div className="restrictions-section">
                            <h4>Schema & Table Restrictions (Optional)</h4>
                            <div className="form-group">
                                <label>Allowed Schemas (comma-separated, leave empty for all)</label>
                                <input
                                    type="text"
                                    value={allowedSchemas}
                                    onChange={(e) => setAllowedSchemas(e.target.value)}
                                    placeholder="e.g., public, analytics, reporting"
                                />
                                <small className="help-text">Leave empty to allow all schemas</small>
                            </div>
                            <div className="form-group">
                                <label>Denied Tables (comma-separated)</label>
                                <input
                                    type="text"
                                    value={deniedTables}
                                    onChange={(e) => setDeniedTables(e.target.value)}
                                    placeholder="e.g., sensitive_data, audit_logs"
                                />
                                <small className="help-text">Tables the user cannot access</small>
                            </div>
                        </div>

                        <button className="btn btn-primary" onClick={handleGrantPermission}>
                            Grant Permission
                        </button>
                    </div>

                    {/* Permissions List */}
                    <div className="permissions-list-section">
                        <h3>Current Permissions</h3>

                        {loading ? (
                            <div className="loading-state">
                                <div className="spinner"></div>
                                <p>Loading permissions...</p>
                            </div>
                        ) : permissions.length === 0 ? (
                            <div className="empty-state">
                                <p>No permissions granted yet</p>
                            </div>
                        ) : (
                            <table className="permissions-table">
                                <thead>
                                    <tr>
                                        <th>User</th>
                                        <th>Read</th>
                                        <th>Write</th>
                                        <th>Execute DDL</th>
                                        <th>Restrictions</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {permissions.map(perm => (
                                        <tr key={perm.id}>
                                            <td>
                                                <div className="user-info">
                                                    <span className="user-email">{perm.user_email}</span>
                                                    <span className="user-id">ID: {perm.user_id}</span>
                                                </div>
                                            </td>
                                            <td>
                                                <span className={`badge ${perm.can_read ? 'badge-success' : 'badge-disabled'}`}>
                                                    {perm.can_read ? '✓' : '✗'}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`badge ${perm.can_write ? 'badge-success' : 'badge-disabled'}`}>
                                                    {perm.can_write ? '✓' : '✗'}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`badge ${perm.can_execute_ddl ? 'badge-success' : 'badge-disabled'}`}>
                                                    {perm.can_execute_ddl ? '✓' : '✗'}
                                                </span>
                                            </td>
                                            <td>
                                                <div className="restrictions-info">
                                                    {perm.allowed_schemas && perm.allowed_schemas.length > 0 && (
                                                        <div className="restriction-item">
                                                            <small>Schemas: {perm.allowed_schemas.join(', ')}</small>
                                                        </div>
                                                    )}
                                                    {perm.denied_tables && perm.denied_tables.length > 0 && (
                                                        <div className="restriction-item">
                                                            <small>Denied: {perm.denied_tables.join(', ')}</small>
                                                        </div>
                                                    )}
                                                    {(!perm.allowed_schemas || perm.allowed_schemas.length === 0) &&
                                                        (!perm.denied_tables || perm.denied_tables.length === 0) && (
                                                            <small className="text-muted">No restrictions</small>
                                                        )}
                                                </div>
                                            </td>
                                            <td>
                                                <button
                                                    className="btn btn-danger btn-sm"
                                                    onClick={() => handleRevokePermission(perm.user_id)}
                                                >
                                                    Revoke
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
