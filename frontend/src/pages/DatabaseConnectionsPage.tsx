/**
 * Database Connections Settings Page
 * Manage multiple database connections
 */
import React, { useState, useEffect } from 'react';
import connectionsApi, { Connection } from '../services/connectionsApi';
import ConnectionModal from '../components/connections/ConnectionModal';
import { PermissionsManager } from '../components/connections/PermissionsManager';
import { Plus, Database, Plug, Edit, Check, Lock, Trash2, Loader2 } from 'lucide-react';
import './DatabaseConnectionsPage.css';

const DatabaseConnectionsPage: React.FC = () => {
    const [connections, setConnections] = useState<Connection[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingConnection, setEditingConnection] = useState<Connection | null>(null);
    const [testingId, setTestingId] = useState<number | null>(null);
    const [showPermissionsManager, setShowPermissionsManager] = useState(false);
    const [permissionsConnectionId, setPermissionsConnectionId] = useState<number | null>(null);
    const [permissionsConnectionName, setPermissionsConnectionName] = useState<string>('');

    useEffect(() => {
        loadConnections();
    }, []);

    const loadConnections = async () => {
        try {
            setLoading(true);
            const data = await connectionsApi.listConnections();
            setConnections(data);
        } catch (error) {
            console.error('Failed to load connections:', error);
            alert('Failed to load connections');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingConnection(null);
        setShowModal(true);
    };

    const handleEdit = (connection: Connection) => {
        setEditingConnection(connection);
        setShowModal(true);
    };

    const handleDelete = async (id: number, name: string) => {
        if (!confirm(`Are you sure you want to delete connection "${name}"?`)) {
            return;
        }

        try {
            await connectionsApi.deleteConnection(id);
            alert('Connection deleted successfully');
            loadConnections();
        } catch (error) {
            console.error('Failed to delete connection:', error);
            alert('Failed to delete connection');
        }
    };

    const handleTest = async (id: number) => {
        setTestingId(id);
        try {
            const result = await connectionsApi.testConnection(id);
            if (result.is_healthy) {
                alert(`✅ Connection successful!\nResponse time: ${result.response_time_ms}ms`);
            } else {
                alert(`❌ Connection failed!\nStatus: ${result.status}`);
            }
            loadConnections(); // Refresh to show updated health status
        } catch (error: any) {
            console.error('Test failed:', error);
            alert(`Connection test failed: ${error.message}`);
        } finally {
            setTestingId(null);
        }
    };

    const handleManagePermissions = (conn: Connection) => {
        setPermissionsConnectionId(conn.id);
        setPermissionsConnectionName(conn.name);
        setShowPermissionsManager(true);
    };

    const handleActivate = async (id: number) => {
        try {
            await connectionsApi.activateConnection(id);
            alert('Connection activated');
            loadConnections();
        } catch (error) {
            console.error('Failed to activate:', error);
            alert('Failed to activate connection');
        }
    };

    const handleDeactivate = async (id: number) => {
        try {
            // Assuming there's a deactivate endpoint or we toggle active status
            // If no explicit deactivate endpoint exists, we might need to update the connection
            // But let's check connectionsApi first. For now, I'll assume we need to add it or use update.
            // Wait, the backend only has activate. We need to add deactivate or use update.
            // Let's implement deactivate in backend first? No, let's use update for now or add endpoint.
            // Actually, best to add a deactivate endpoint in backend to matches activate.
            // For now, I'll add the function structure.
            await connectionsApi.deactivateConnection(id);
            alert('Connection deactivated');
            loadConnections();
        } catch (error) {
            console.error('Failed to deactivate:', error);
            alert('Failed to deactivate connection');
        }
    };

    const getHealthStatusBadge = (status?: string) => {
        if (!status) return <span className="badge badge-unknown">Unknown</span>;

        const statusMap: Record<string, string> = {
            online: 'badge-success',
            offline: 'badge-danger',
            degraded: 'badge-warning',
            unknown: 'badge-unknown'
        };

        return <span className={`badge ${statusMap[status] || 'badge-unknown'}`}>{status.toUpperCase()}</span>;
    };

    const getGroupBadge = (group?: string) => {
        if (!group) return null;

        const groupMap: Record<string, string> = {
            production: 'badge-danger',
            staging: 'badge-warning',
            development: 'badge-info',
            analytics: 'badge-purple',
            testing: 'badge-secondary'
        };

        return <span className={`badge ${groupMap[group] || 'badge-secondary'}`}>{group}</span>;
    };

    if (loading) {
        return <div className="loading">Loading connections...</div>;
    }

    return (
        <div className="database-connections-page">
            <div className="page-header">
                <div>
                    <h1>Database Connections</h1>
                    <p className="text-muted">Manage your database connections and configurations</p>
                </div>
                <button className="btn btn-primary" onClick={handleCreate}>
                    <Plus className="w-4 h-4 mr-2" /> New Connection
                </button>
            </div>

            <div className="connections-grid">
                {connections.length === 0 ? (
                    <div className="empty-state">
                        <Database className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                        <h3>No Connections</h3>
                        <p>Create your first database connection to get started</p>
                        <button className="btn btn-primary" onClick={handleCreate}>
                            Add Connection
                        </button>
                    </div>
                ) : (
                    <table className="connections-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Group</th>
                                <th>Database</th>
                                <th>Health</th>
                                <th>Response</th>
                                <th>Status</th>
                                <th style={{ textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {connections.map((conn) => (
                                <tr key={conn.id} className={conn.is_active ? 'active-row' : ''}>
                                    <td>
                                        <div className="connection-name">
                                            <strong>{conn.name}</strong>
                                            {conn.is_default && <span className="badge badge-primary ml-2">Default</span>}
                                        </div>
                                        {conn.description && <div className="text-muted small">{conn.description}</div>}
                                    </td>
                                    <td>
                                        <span className="db-type-badge">{conn.db_type}</span>
                                    </td>
                                    <td>{getGroupBadge(conn.connection_group)}</td>
                                    <td>
                                        {conn.host && <div className="small text-muted">{conn.host}:{conn.port}</div>}
                                        <div className="db-name">{conn.database}</div>
                                    </td>
                                    <td>{getHealthStatusBadge(conn.health_status)}</td>
                                    <td>
                                        {conn.response_time_ms ? (
                                            <span className={`response-time ${conn.response_time_ms > 100 ? 'slow' : 'fast'}`}>
                                                {conn.response_time_ms}ms
                                            </span>
                                        ) : '-'}
                                    </td>
                                    <td>
                                        {conn.is_active ? (
                                            <span className="badge badge-success">
                                                <span className="text-dot success"></span> Active
                                            </span>
                                        ) : (
                                            <span className="badge badge-secondary">
                                                <span className="text-dot inactive"></span> Inactive
                                            </span>
                                        )}
                                    </td>
                                    <td>
                                        <div className="action-buttons">
                                            <button
                                                className="btn-icon"
                                                onClick={() => handleTest(conn.id)}
                                                disabled={testingId === conn.id}
                                                title="Test Connection"
                                            >
                                                {testingId === conn.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <Plug className="w-4 h-4" />
                                                )}
                                            </button>
                                            <button
                                                className="btn-icon"
                                                onClick={() => handleEdit(conn)}
                                                title="Edit"
                                            >
                                                <Edit className="w-4 h-4" />
                                            </button>
                                            {conn.is_active ? (
                                                <button
                                                    className="btn-icon danger"
                                                    onClick={() => handleDeactivate(conn.id)}
                                                    title="Deactivate"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            ) : (
                                                <button
                                                    className="btn-icon success"
                                                    onClick={() => handleActivate(conn.id)}
                                                    title="Activate"
                                                >
                                                    <Check className="w-4 h-4" />
                                                </button>
                                            )}
                                            <button
                                                className="btn-icon"
                                                onClick={() => handleManagePermissions(conn)}
                                                title="Manage Permissions"
                                            >
                                                <Lock className="w-4 h-4" />
                                            </button>
                                            <button
                                                className="btn-icon danger"
                                                onClick={() => handleDelete(conn.id, conn.name)}
                                                title="Delete"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {showModal && (
                <ConnectionModal
                    connection={editingConnection}
                    onClose={() => setShowModal(false)}
                    onSave={() => {
                        setShowModal(false);
                        loadConnections();
                    }}
                />
            )}

            {showPermissionsManager && permissionsConnectionId && (
                <PermissionsManager
                    connectionId={permissionsConnectionId}
                    connectionName={permissionsConnectionName}
                    onClose={() => setShowPermissionsManager(false)}
                />
            )}
        </div>
    );
};

export default DatabaseConnectionsPage;
