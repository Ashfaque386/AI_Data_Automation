import React, { useState } from 'react'
import { editOperationsApi, ChangeHistoryItem } from '../services/editOperationsApi'
import './VersionHistoryViewer.css'

interface VersionHistoryViewerProps {
    datasetId: number
    onClose: () => void
}

export const VersionHistoryViewer: React.FC<VersionHistoryViewerProps> = ({ datasetId, onClose }) => {
    const [history, setHistory] = useState<ChangeHistoryItem[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState<'all' | 'committed' | 'uncommitted'>('all')

    React.useEffect(() => {
        loadHistory()
    }, [datasetId, filter])

    const loadHistory = async () => {
        setLoading(true)
        try {
            const data = await editOperationsApi.getChangeHistory(
                datasetId,
                100,
                filter === 'committed'
            )
            setHistory(data)
        } catch (error) {
            console.error('Failed to load history:', error)
        } finally {
            setLoading(false)
        }
    }

    const getChangeIcon = (type: string) => {
        switch (type) {
            case 'cell_edit': return '✏️'
            case 'row_add': return '➕'
            case 'row_delete': return '🗑️'
            case 'column_add': return '📊'
            case 'column_delete': return '❌'
            case 'column_rename': return '🔄'
            default: return '📝'
        }
    }

    const formatChangeDescription = (change: ChangeHistoryItem) => {
        switch (change.change_type) {
            case 'cell_edit':
                return (
                    <div className="change-detail">
                        <strong>{change.column_name}</strong> at row {change.row_index}
                        <div className="value-change">
                            <span className="old-value">"{String(change.old_value)}"</span>
                            <span className="arrow">→</span>
                            <span className="new-value">"{String(change.new_value)}"</span>
                        </div>
                    </div>
                )
            case 'row_add':
                return `Added row at position ${change.row_index}`
            case 'row_delete':
                return `Deleted row ${change.row_index}`
            case 'column_add':
                return `Added column "${change.column_name}"`
            case 'column_delete':
                return `Deleted column "${change.column_name}"`
            case 'column_rename':
                return `Renamed column "${change.old_value}" to "${change.new_value}"`
            default:
                return `${change.change_type} operation`
        }
    }

    const groupByDate = (changes: ChangeHistoryItem[]) => {
        const groups: { [key: string]: ChangeHistoryItem[] } = {}
        changes.forEach(change => {
            const date = new Date(change.timestamp).toLocaleDateString()
            if (!groups[date]) {
                groups[date] = []
            }
            groups[date].push(change)
        })
        return groups
    }

    const grouped = groupByDate(history)

    return (
        <div className="version-history-viewer">
            <div className="history-header">
                <h2>📜 Version History</h2>
                <button className="close-btn" onClick={onClose}>✖</button>
            </div>

            <div className="history-filters">
                <button
                    className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                    onClick={() => setFilter('all')}
                >
                    All Changes
                </button>
                <button
                    className={`filter-btn ${filter === 'committed' ? 'active' : ''}`}
                    onClick={() => setFilter('committed')}
                >
                    Committed Only
                </button>
                <button
                    className={`filter-btn ${filter === 'uncommitted' ? 'active' : ''}`}
                    onClick={() => setFilter('uncommitted')}
                >
                    Uncommitted Only
                </button>
            </div>

            <div className="history-content">
                {loading ? (
                    <div className="loading-state">
                        <div className="spinner"></div>
                        <p>Loading history...</p>
                    </div>
                ) : Object.keys(grouped).length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon">📭</div>
                        <p>No changes found</p>
                    </div>
                ) : (
                    Object.entries(grouped).map(([date, changes]) => (
                        <div key={date} className="date-group">
                            <div className="date-header">{date}</div>
                            <div className="changes-list">
                                {changes.map(change => (
                                    <div
                                        key={change.id}
                                        className={`history-item ${change.is_committed ? 'committed' : 'uncommitted'}`}
                                    >
                                        <div className="change-icon">{getChangeIcon(change.change_type)}</div>
                                        <div className="change-content">
                                            <div className="change-description">
                                                {formatChangeDescription(change)}
                                            </div>
                                            <div className="change-meta">
                                                <span className="timestamp">
                                                    {new Date(change.timestamp).toLocaleTimeString()}
                                                </span>
                                                <span className={`status-badge ${change.is_committed ? 'committed' : 'uncommitted'}`}>
                                                    {change.is_committed ? '✓ Committed' : '⏳ Pending'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
