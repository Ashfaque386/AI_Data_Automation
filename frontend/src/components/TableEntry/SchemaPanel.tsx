/**
 * Schema Panel Component
 * Displays table structure in read-only format
 */
import React, { useState } from 'react'
import { ColumnMetadata } from '../../services/tableEntryApi'
import './SchemaPanel.css'

interface SchemaPanelProps {
    columns: ColumnMetadata[]
}

export const SchemaPanel: React.FC<SchemaPanelProps> = ({ columns }) => {
    const [isExpanded, setIsExpanded] = useState(false)

    return (
        <div className="schema-panel">
            <div className="schema-panel-header" onClick={() => setIsExpanded(!isExpanded)}>
                <h3>📋 Table Schema</h3>
                <button className="toggle-btn">
                    {isExpanded ? '▼ Collapse' : '▶ Expand'}
                </button>
            </div>

            {isExpanded && (
                <div className="schema-panel-content">
                    <table className="schema-table">
                        <thead>
                            <tr>
                                <th>Column</th>
                                <th>Data Type</th>
                                <th>Nullable</th>
                                <th>Default</th>
                                <th>Constraints</th>
                            </tr>
                        </thead>
                        <tbody>
                            {columns.map((col) => (
                                <tr key={col.name}>
                                    <td className="column-name">
                                        {col.name}
                                        {col.autoincrement && <span className="badge auto">AUTO</span>}
                                    </td>
                                    <td className="column-type">{col.type}</td>
                                    <td className="column-nullable">
                                        {col.nullable ? (
                                            <span className="nullable-yes">✓ Yes</span>
                                        ) : (
                                            <span className="nullable-no">✗ No</span>
                                        )}
                                    </td>
                                    <td className="column-default">
                                        {col.default || <span className="null-value">NULL</span>}
                                    </td>
                                    <td className="column-constraints">
                                        {col.is_primary_key && <span className="badge pk">PK</span>}
                                        {col.is_foreign_key && (
                                            <span className="badge fk" title={`References ${col.foreign_key_ref?.referenced_table}.${col.foreign_key_ref?.referenced_column}`}>
                                                FK
                                            </span>
                                        )}
                                        {col.is_unique && <span className="badge unique">UNIQUE</span>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
