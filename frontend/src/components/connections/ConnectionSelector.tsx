/**
 * Connection Selector Component
 * Dropdown to select active database connection
 */
import React, { useState, useEffect } from 'react';
import connectionsApi, { Connection } from '../../services/connectionsApi';
import './ConnectionSelector.css';

interface ConnectionSelectorProps {
    selectedConnectionId?: number;
    onConnectionChange: (connectionId: number) => void;
    showHealthStatus?: boolean;
}

const ConnectionSelector: React.FC<ConnectionSelectorProps> = ({
    selectedConnectionId,
    onConnectionChange,
    showHealthStatus = true
}) => {
    const [connections, setConnections] = useState<Connection[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadConnections();
    }, []);

    const loadConnections = async () => {
        try {
            const data = await connectionsApi.listConnections();
            const activeConnections = data.filter(conn => conn.is_active);
            setConnections(activeConnections);

            // Auto-select default or first connection if none selected
            if (!selectedConnectionId && activeConnections.length > 0) {
                const defaultConn = activeConnections.find(c => c.is_default) || activeConnections[0];
                onConnectionChange(defaultConn.id);
            }
        } catch (error) {
            console.error('Failed to load connections:', error);
        } finally {
            setLoading(false);
        }
    };

    const getHealthIcon = (status?: string) => {
        if (!status) return null;

        const iconMap: Record<string, { icon: string; color: string }> = {
            online: { icon: '●', color: '#4caf50' },
            offline: { icon: '●', color: '#f44336' },
            degraded: { icon: '●', color: '#ff9800' },
            unknown: { icon: '●', color: '#9e9e9e' }
        };

        const config = iconMap[status] || iconMap.unknown;
        return <span style={{ color: config.color }}>{config.icon}</span>;
    };

    if (loading) {
        return <div className="connection-selector loading">Loading...</div>;
    }

    if (connections.length === 0) {
        return (
            <div className="connection-selector empty">
                <i className="fas fa-exclamation-triangle"></i>
                No active connections
            </div>
        );
    }

    return (
        <div className="connection-selector">
            <label className="selector-label">
                <i className="fas fa-database"></i>
                Database Connection
            </label>
            <select
                className="connection-select"
                value={selectedConnectionId || ''}
                onChange={(e) => onConnectionChange(parseInt(e.target.value))}
            >
                {connections.map((conn) => (
                    <option key={conn.id} value={conn.id}>
                        {showHealthStatus && getHealthIcon(conn.health_status)} {conn.name} ({conn.db_type})
                        {conn.response_time_ms && ` - ${conn.response_time_ms}ms`}
                    </option>
                ))}
            </select>
        </div>
    );
};

export default ConnectionSelector;
