import React from 'react'
import './ChangeSummaryPanel.css'

interface Change {
    id: number
    change_type: string
    row_index?: number
    column_name?: string
    old_value: any
    new_value: any
    timestamp: string
    is_committed: boolean
}

interface ChangeSummaryPanelProps {
    changes: Change[]
    onClose: () => void
}

export const ChangeSummaryPanel: React.FC<ChangeSummaryPanelProps> = ({ changes, onClose }) => {
    const uncommittedChanges = changes.filter(c => !c.is_committed)
    const committedChanges = changes.filter(c => c.is_committed)

    const getChangeIcon = (type: string) => {
        switch (type) {
            case 'cell_edit': return '✏️'
            case 'row_add': return '➕'
            case 'row_delete': return '🗑️'
            case 'column_add': return '📊'
            case 'column_delete': return '❌'
            default: return '📝'
        }
    }

    const formatChangeDescription = (change: Change) => {
        switch (change.change_type) {
            case 'cell_edit':
                return `Edited ${change.column_name} at row ${change.row_index}: "${change.old_value}" → "${change.new_value}"`
            case 'row_add':
                return `Added row at position ${change.row_index}`
            case 'row_delete':
                return `Deleted row ${change.row_index}`
            case 'column_add':
                return `Added column "${change.column_name}"`
            case 'column_delete':
                return `Deleted column "${change.column_name}"`
            default:
                return `${change.change_type} operation`
        }
    }

    return (
        <div className="change-summary-panel">
            <div className="panel-header">
                <h3>📋 Change Summary</h3>
                <button className="close-btn" onClick={onClose}>✖</button>
            </div>

            <div className="panel-content">
                {uncommittedChanges.length > 0 && (
                    <div className="change-section">
                        <h4 className="section-title uncommitted">
                            ⚠️ Uncommitted Changes ({uncommittedChanges.length})
                        </h4>
                        <div className="change-list">
                            {uncommittedChanges.map(change => (
                                <div key={change.id} className="change-item uncommitted">
                                    <span className="change-icon">{getChangeIcon(change.change_type)}</span>
                                    <div className="change-details">
                                        <div className="change-description">
                                            {formatChangeDescription(change)}
                                        </div>
                                        <div className="change-timestamp">
                                            {new Date(change.timestamp).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {committedChanges.length > 0 && (
                    <div className="change-section">
                        <h4 className="section-title committed">
                            ✅ Recent Committed Changes ({committedChanges.length})
                        </h4>
                        <div className="change-list">
                            {committedChanges.slice(0, 10).map(change => (
                                <div key={change.id} className="change-item committed">
                                    <span className="change-icon">{getChangeIcon(change.change_type)}</span>
                                    <div className="change-details">
                                        <div className="change-description">
                                            {formatChangeDescription(change)}
                                        </div>
                                        <div className="change-timestamp">
                                            {new Date(change.timestamp).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {changes.length === 0 && (
                    <div className="empty-state">
                        <div className="empty-icon">📝</div>
                        <p>No changes yet</p>
                    </div>
                )}
            </div>
        </div>
    )
}
