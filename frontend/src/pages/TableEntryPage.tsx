/**
 * Table Entry Page
 * Direct database table row insertion with Excel-style editing
 */
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { tableEntryApi, ConnectionInfo } from '../services/tableEntryApi'
import { SchemaTableSelector } from '../components/TableEntry/SchemaTableSelector'
import { SchemaPanel } from '../components/TableEntry/SchemaPanel'
import { DataEntryGrid } from '../components/TableEntry/DataEntryGrid'
import './TableEntryPage.css'

export const TableEntryPage: React.FC = () => {
    const [selectedConnection, setSelectedConnection] = useState<ConnectionInfo | null>(null)
    const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
    const [selectedTable, setSelectedTable] = useState<string | null>(null)

    // Fetch available connections
    const { data: connections, isLoading: connectionsLoading } = useQuery({
        queryKey: ['table-entry-connections'],
        queryFn: () => tableEntryApi.getConnections()
    })

    // Fetch table metadata when table is selected
    const { data: tableMetadata, isLoading: metadataLoading } = useQuery({
        queryKey: ['table-entry-metadata', selectedConnection?.id, selectedSchema, selectedTable],
        queryFn: () => tableEntryApi.getTableSchema(selectedConnection!.id, selectedSchema!, selectedTable!),
        enabled: !!selectedConnection && !!selectedSchema && !!selectedTable
    })

    const handleConnectionSelect = (connection: ConnectionInfo) => {
        setSelectedConnection(connection)
        setSelectedSchema(null)
        setSelectedTable(null)
    }

    const handleTableSelect = (schema: string, table: string) => {
        setSelectedSchema(schema)
        setSelectedTable(table)
    }

    const handleBack = () => {
        if (selectedTable) {
            setSelectedTable(null)
            setSelectedSchema(null)
        } else {
            setSelectedConnection(null)
        }
    }

    if (connectionsLoading) {
        return (
            <div className="table-entry-page">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading connections...</p>
                </div>
            </div>
        )
    }

    if (!connections || connections.length === 0) {
        return (
            <div className="table-entry-page">
                <div className="page-header">
                    <h1>➕ Table Data Entry</h1>
                    <p className="subtitle">Direct database table row insertion with Excel-style editing</p>
                </div>

                <div className="empty-state">
                    <div className="empty-icon">🔌</div>
                    <h2>No Database Connections</h2>
                    <p>Please configure a database connection in Settings before using Table Data Entry.</p>
                    <a href="/settings" className="btn btn-primary">
                        Go to Settings
                    </a>
                </div>
            </div>
        )
    }

    return (
        <div className="table-entry-page">
            <div className="page-header">
                <h1>➕ Table Data Entry</h1>
                <p className="subtitle">Direct database table row insertion with Excel-style editing</p>
            </div>

            {!selectedConnection ? (
                // Step 1: Connection Selection
                <div className="workflow-step">
                    <div className="step-indicator">
                        <span className="step-number">1</span>
                        <span className="step-title">Select Database Connection</span>
                    </div>

                    <div className="connection-grid">
                        {connections.map((conn) => (
                            <button
                                key={conn.id}
                                className={`connection-card ${conn.is_active ? 'active' : ''}`}
                                onClick={() => handleConnectionSelect(conn)}
                            >
                                <div className="connection-icon">🗄️</div>
                                <div className="connection-info">
                                    <h3>{conn.name}</h3>
                                    <p>{conn.database} @ {conn.host}</p>
                                </div>
                                {conn.is_active && <span className="active-badge">Active</span>}
                            </button>
                        ))}
                    </div>
                </div>
            ) : !selectedTable ? (
                // Step 2: Schema and Table Selection
                <div className="workflow-step">
                    <div className="step-header">
                        <button className="btn btn-outline" onClick={handleBack}>
                            ← Back to Connections
                        </button>
                        <div className="selected-connection-info">
                            <span className="connection-badge">
                                🗄️ {selectedConnection.name}
                            </span>
                        </div>
                    </div>

                    <div className="step-indicator">
                        <span className="step-number">2</span>
                        <span className="step-title">Select Schema & Table</span>
                    </div>

                    <SchemaTableSelector
                        connectionId={selectedConnection.id}
                        onSelect={handleTableSelect}
                    />
                </div>
            ) : (
                // Step 3: Data Entry
                <div className="workflow-step">
                    <div className="step-header">
                        <button className="btn btn-outline" onClick={handleBack}>
                            ← Back to Table Selection
                        </button>
                        <div className="selected-table-info">
                            <span className="connection-badge">🗄️ {selectedConnection.name}</span>
                            <span className="table-badge">📋 {selectedSchema}.{selectedTable}</span>
                        </div>
                    </div>

                    {metadataLoading ? (
                        <div className="loading-container">
                            <div className="spinner"></div>
                            <p>Loading table schema...</p>
                        </div>
                    ) : tableMetadata ? (
                        <>
                            <SchemaPanel columns={tableMetadata.columns} />
                            <DataEntryGrid
                                connectionId={selectedConnection.id}
                                schema={selectedSchema}
                                table={selectedTable}
                                columns={tableMetadata.columns}
                            />
                        </>
                    ) : (
                        <div className="error-state">
                            <p>Failed to load table metadata</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
