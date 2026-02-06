/**
 * Connection Selector Component
 * Displays available database connections for selection
 */
import React from 'react'
import { ConnectionInfo } from '../../services/tableEntryApi'
import './ConnectionSelector.css'

interface ConnectionSelectorProps {
    connections: ConnectionInfo[]
    selectedConnection: ConnectionInfo | null
    onSelect: (connection: ConnectionInfo) => void
    isLoading: boolean
}

export const ConnectionSelector: React.FC<ConnectionSelectorProps> = ({
    connections,
    selectedConnection,
    onSelect,
    isLoading
}) => {
    if (isLoading) {
        return (
            <div className="connection-selector-loading">
                <div className="spinner"></div>
                <p>Loading connections...</p>
            </div>
        )
    }

    if (connections.length === 0) {
        return (
            <div className="connection-selector-empty">
                <div className="empty-icon">🔌</div>
                <h3>No Connections Available</h3>
                <p>Please create a database connection first in the Connections page.</p>
            </div>
        )
    }

    return (
        <div className="connection-selector">
            <div className="connection-grid">
                {connections.map((connection) => (
                    <div
                        key={connection.id}
                        className={`connection-card ${selectedConnection?.id === connection.id ? 'selected' : ''}`}
                        onClick={() => onSelect(connection)}
                    >
                        <div className="connection-icon">
                            {connection.db_type === 'postgresql' ? '🐘' : '🐬'}
                        </div>
                        <div className="connection-details">
                            <h3>{connection.name}</h3>
                            <div className="connection-meta">
                                <span className="meta-item">
                                    <span className="meta-label">Type:</span>
                                    <span className="meta-value">{connection.db_type}</span>
                                </span>
                                <span className="meta-item">
                                    <span className="meta-label">Host:</span>
                                    <span className="meta-value">{connection.host}</span>
                                </span>
                                <span className="meta-item">
                                    <span className="meta-label">Database:</span>
                                    <span className="meta-value">{connection.database}</span>
                                </span>
                            </div>
                        </div>
                        <div className={`connection-status ${connection.status}`}>
                            <span className="status-dot"></span>
                            {connection.status}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
