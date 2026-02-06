/**
 * Schema and Table Selector Component
 * Allows users to browse and select a table from a specific database connection
 */
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { tableEntryApi, TableInfo } from '../../services/tableEntryApi'
import './SchemaTableSelector.css'

interface Props {
    connectionId: number
    onSelect: (schema: string, table: string) => void
}

export const SchemaTableSelector: React.FC<Props> = ({ connectionId, onSelect }) => {
    const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
    const [searchTerm, setSearchTerm] = useState('')

    // Fetch schemas for the connection
    const { data: schemas, isLoading: schemasLoading } = useQuery({
        queryKey: ['table-entry-schemas', connectionId],
        queryFn: () => tableEntryApi.getSchemas(connectionId)
    })

    // Fetch tables for selected schema
    const { data: tables, isLoading: tablesLoading } = useQuery({
        queryKey: ['table-entry-tables', connectionId, selectedSchema],
        queryFn: () => tableEntryApi.getTables(connectionId, selectedSchema!),
        enabled: !!selectedSchema
    })

    const filteredTables = tables?.filter((t: TableInfo) =>
        t.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) || []

    const handleSchemaSelect = (schema: string) => {
        setSelectedSchema(schema)
        setSearchTerm('')
    }

    const handleTableSelect = (table: TableInfo) => {
        onSelect(selectedSchema!, table.name)
    }

    return (
        <div className="schema-table-selector">
            {/* Schema Selection */}
            <div className="selector-section">
                <h3>📁 Select Schema</h3>
                {schemasLoading ? (
                    <div className="loading-state">
                        <div className="spinner-small"></div>
                        <span>Loading schemas...</span>
                    </div>
                ) : schemas && schemas.length > 0 ? (
                    <div className="schema-grid">
                        {schemas.map((schema: string) => (
                            <button
                                key={schema}
                                className={`schema-card ${selectedSchema === schema ? 'selected' : ''}`}
                                onClick={() => handleSchemaSelect(schema)}
                            >
                                <span className="schema-icon">📂</span>
                                <span className="schema-name">{schema}</span>
                            </button>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state-small">
                        <p>No schemas found</p>
                    </div>
                )}
            </div>

            {/* Table Selection */}
            {selectedSchema && (
                <div className="selector-section">
                    <div className="section-header">
                        <h3>📋 Select Table from "{selectedSchema}"</h3>
                        <input
                            type="text"
                            className="table-search"
                            placeholder="Search tables..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    {tablesLoading ? (
                        <div className="loading-state">
                            <div className="spinner-small"></div>
                            <span>Loading tables...</span>
                        </div>
                    ) : filteredTables.length > 0 ? (
                        <div className="table-list">
                            {filteredTables.map((table: TableInfo) => (
                                <button
                                    key={table.name}
                                    className="table-card"
                                    onClick={() => handleTableSelect(table)}
                                >
                                    <div className="table-info">
                                        <span className="table-icon">📄</span>
                                        <div className="table-details">
                                            <span className="table-name">{table.name}</span>
                                            {table.row_count !== null && (
                                                <span className="table-rows">
                                                    {table.row_count.toLocaleString()} rows
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <span className="select-arrow">→</span>
                                </button>
                            ))}
                        </div>
                    ) : (
                        <div className="empty-state-small">
                            <p>No tables found {searchTerm && `matching "${searchTerm}"`}</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
