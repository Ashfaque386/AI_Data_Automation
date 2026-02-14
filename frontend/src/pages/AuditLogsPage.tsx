/**
 * Audit Logs Page
 * View and filter system audit logs
 */
import React, { useState, useEffect } from 'react';
import { auditApi, AuditLog, AuditStats } from '../services/auditApi';
import connectionsApi, { Connection } from '../services/connectionsApi';
import './AuditLogsPage.css';

export const AuditLogsPage: React.FC = () => {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [stats, setStats] = useState<AuditStats | null>(null);
    const [connections, setConnections] = useState<Connection[]>([]);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    // Filters
    const [connectionFilter, setConnectionFilter] = useState<string>('');
    const [actionTypeFilter, setActionTypeFilter] = useState<string>('');
    const [resourceTypeFilter, setResourceTypeFilter] = useState<string>('');
    const [statusFilter, setStatusFilter] = useState<string>('');
    const [dateRange, setDateRange] = useState<number>(7); // days
    const [limit, setLimit] = useState<number>(100);

    useEffect(() => {
        loadData();
    }, [connectionFilter, actionTypeFilter, resourceTypeFilter, statusFilter, dateRange, limit]);

    const loadData = async () => {
        try {
            setLoading(true);

            // Calculate date range
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - dateRange);

            // Build params
            const params: any = {
                limit,
                start_date: startDate.toISOString(),
                end_date: endDate.toISOString()
            };

            if (connectionFilter) params.connection_id = parseInt(connectionFilter);
            if (actionTypeFilter) params.action_type = actionTypeFilter;
            if (resourceTypeFilter) params.resource_type = resourceTypeFilter;
            if (statusFilter === 'success') params.success_only = true;
            if (statusFilter === 'failure') params.success_only = false;

            // Load logs and stats in parallel
            const [logsData, statsData, connectionsData] = await Promise.all([
                auditApi.getLogs(params),
                auditApi.getStats({ days: dateRange }),
                connectionsApi.listConnections()
            ]);

            setLogs(logsData);
            setStats(statsData);
            setConnections(connectionsData);
        } catch (error) {
            console.error('Failed to load audit logs:', error);
            alert('Failed to load audit logs');
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format: 'csv' | 'json') => {
        try {
            setExporting(true);

            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - dateRange);

            const params: any = {
                start_date: startDate.toISOString(),
                end_date: endDate.toISOString()
            };

            if (connectionFilter) params.connection_id = parseInt(connectionFilter);
            if (actionTypeFilter) params.action_type = actionTypeFilter;
            if (resourceTypeFilter) params.resource_type = resourceTypeFilter;

            const blob = await auditApi.exportLogs(format, params);

            // Download file
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Failed to export logs:', error);
            alert('Failed to export logs');
        } finally {
            setExporting(false);
        }
    };

    const formatTimestamp = (timestamp: string) => {
        return new Date(timestamp).toLocaleString();
    };

    const getStatusBadgeClass = (status: string) => {
        return status === 'success' ? 'badge-success' : 'badge-error';
    };

    const getActionTypeLabel = (actionType?: string) => {
        if (!actionType) return 'N/A';
        return actionType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    return (
        <div className="audit-logs-page">
            <div className="page-header">
                <h1>📋 Audit Logs</h1>
                <p className="subtitle">Track all system operations and security events</p>
            </div>

            {/* Statistics Dashboard */}
            {stats && (
                <div className="stats-dashboard">
                    <div className="stat-card">
                        <div className="stat-icon">📊</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.total_actions.toLocaleString()}</div>
                            <div className="stat-label">Total Actions</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon">✅</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.successful_actions.toLocaleString()}</div>
                            <div className="stat-label">Successful</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon">❌</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.failed_actions.toLocaleString()}</div>
                            <div className="stat-label">Failed</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon">📈</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.success_rate.toFixed(1)}%</div>
                            <div className="stat-label">Success Rate</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="filters-section">
                <div className="filter-group">
                    <label>Connection</label>
                    <select value={connectionFilter} onChange={(e) => setConnectionFilter(e.target.value)}>
                        <option value="">All Connections</option>
                        {connections.map(conn => (
                            <option key={conn.id} value={conn.id}>{conn.name}</option>
                        ))}
                    </select>
                </div>

                <div className="filter-group">
                    <label>Action Type</label>
                    <select value={actionTypeFilter} onChange={(e) => setActionTypeFilter(e.target.value)}>
                        <option value="">All Actions</option>
                        <option value="connection_create">Connection Create</option>
                        <option value="connection_update">Connection Update</option>
                        <option value="connection_delete">Connection Delete</option>
                        <option value="connection_test">Connection Test</option>
                        <option value="query_execute">Query Execute</option>
                        <option value="data_import">Data Import</option>
                        <option value="data_export">Data Export</option>
                        <option value="permission_grant">Permission Grant</option>
                        <option value="permission_revoke">Permission Revoke</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Resource Type</label>
                    <select value={resourceTypeFilter} onChange={(e) => setResourceTypeFilter(e.target.value)}>
                        <option value="">All Resources</option>
                        <option value="connection">Connection</option>
                        <option value="query">Query</option>
                        <option value="schema">Schema</option>
                        <option value="table">Table</option>
                        <option value="permission">Permission</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Status</label>
                    <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                        <option value="">All Statuses</option>
                        <option value="success">Success Only</option>
                        <option value="failure">Failures Only</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Date Range</label>
                    <select value={dateRange} onChange={(e) => setDateRange(parseInt(e.target.value))}>
                        <option value="1">Last 24 Hours</option>
                        <option value="7">Last 7 Days</option>
                        <option value="30">Last 30 Days</option>
                        <option value="90">Last 90 Days</option>
                    </select>
                </div>

                <div className="filter-group">
                    <label>Limit</label>
                    <select value={limit} onChange={(e) => setLimit(parseInt(e.target.value))}>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="500">500</option>
                        <option value="1000">1000</option>
                    </select>
                </div>
            </div>

            {/* Actions */}
            <div className="actions-bar">
                <button className="btn btn-outline" onClick={() => loadData()} disabled={loading}>
                    🔄 Refresh
                </button>
                <button className="btn btn-outline" onClick={() => handleExport('csv')} disabled={exporting}>
                    📥 Export CSV
                </button>
                <button className="btn btn-outline" onClick={() => handleExport('json')} disabled={exporting}>
                    📥 Export JSON
                </button>
            </div>

            {/* Logs Table */}
            {loading ? (
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading audit logs...</p>
                </div>
            ) : logs.length === 0 ? (
                <div className="empty-state">
                    <div className="empty-icon">📋</div>
                    <h2>No Audit Logs Found</h2>
                    <p>No logs match your current filters.</p>
                </div>
            ) : (
                <div className="logs-table-container">
                    <table className="logs-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>User</th>
                                <th>Action</th>
                                <th>Resource</th>
                                <th>Connection</th>
                                <th>Status</th>
                                <th>Duration</th>
                                <th>IP Address</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.map(log => (
                                <tr key={log.id}>
                                    <td className="timestamp-cell">{formatTimestamp(log.timestamp)}</td>
                                    <td>{log.user_email || 'System'}</td>
                                    <td>
                                        <span className="action-badge">
                                            {getActionTypeLabel(log.action_type)}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="resource-cell">
                                            <span className="resource-type">{log.resource_type}</span>
                                            {log.resource_name && (
                                                <span className="resource-name">{log.resource_name}</span>
                                            )}
                                        </div>
                                    </td>
                                    <td>{log.connection_name || '-'}</td>
                                    <td>
                                        <span className={`badge ${getStatusBadgeClass(log.status)}`}>
                                            {log.status}
                                        </span>
                                    </td>
                                    <td>{log.duration_ms ? `${log.duration_ms}ms` : '-'}</td>
                                    <td className="ip-cell">{log.ip_address || '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <div className="results-info">
                Showing {logs.length} of {stats?.total_actions || 0} total logs
            </div>
        </div>
    );
};
