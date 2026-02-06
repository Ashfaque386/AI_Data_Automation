/**
 * Data Entry Grid Component
 * Excel-style editable grid with datatype-aware cell editors
 */
import React, { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ColumnMetadata, tableEntryApi } from '../../services/tableEntryApi'
import { DatatypeCell } from './DatatypeCell'
import { ValidationPanel } from './ValidationPanel'
import { InsertControls } from './InsertControls'
import './DataEntryGrid.css'

interface DataEntryGridProps {
    connectionId: number
    schema: string
    table: string
    columns: ColumnMetadata[]
}

export const DataEntryGrid: React.FC<DataEntryGridProps> = ({
    connectionId,
    schema,
    table,
    columns
}) => {
    const queryClient = useQueryClient()
    const [rows, setRows] = useState<Array<Record<string, any>>>([{}])
    const [validationResult, setValidationResult] = useState<any>(null)
    const [insertMode, setInsertMode] = useState<'transaction' | 'row-by-row'>('transaction')

    // Local Storage Key
    const storageKey = `table-entry-draft-${connectionId}-${schema}-${table}`

    // Load drafts on mount
    React.useEffect(() => {
        const savedRows = localStorage.getItem(storageKey)
        if (savedRows) {
            try {
                setRows(JSON.parse(savedRows))
            } catch (e) {
                console.error('Failed to load draft rows', e)
            }
        }
    }, [storageKey])

    // Save drafts on change
    React.useEffect(() => {
        if (rows.length > 0 && Object.keys(rows[0]).length > 0) {
            localStorage.setItem(storageKey, JSON.stringify(rows))
        } else {
            localStorage.removeItem(storageKey)
        }
    }, [rows, storageKey])

    // Filter out autoincrement columns for display
    const editableColumns = columns.filter(col => !col.autoincrement || !col.is_primary_key)

    // Get default values
    const getDefaultRow = () => {
        const defaultRow: Record<string, any> = {}
        columns.forEach(col => {
            if (col.default !== null && col.default !== undefined) {
                if (!col.default.startsWith('nextval') && !col.default.includes('()')) {
                    let val = col.default.split('::')[0].replace(/'/g, "")
                    if (col.type.includes('INT') || col.type.includes('DECIMAL')) {
                        defaultRow[col.name] = Number(val)
                    } else {
                        defaultRow[col.name] = val
                    }
                }
            }
        })
        return defaultRow
    }

    // Add new row with defaults
    const addRow = () => {
        setRows([...rows, getDefaultRow()])
    }

    // Remove row
    const removeRow = (index: number) => {
        const newRows = rows.filter((_, i) => i !== index)
        setRows(newRows)
    }

    // Duplicate row
    const duplicateRow = (index: number) => {
        const newRow = { ...rows[index] }
        setRows([...rows.slice(0, index + 1), newRow, ...rows.slice(index + 1)])
    }

    // Clear row
    const clearRow = (index: number) => {
        const newRows = [...rows]
        newRows[index] = getDefaultRow()
        setRows(newRows)
    }

    // Update cell
    const updateCell = (rowIndex: number, columnName: string, value: any) => {
        const newRows = [...rows]
        newRows[rowIndex] = { ...newRows[rowIndex], [columnName]: value }
        setRows(newRows)
    }

    // Clear all
    const clearAll = () => {
        setRows([getDefaultRow()])
        setValidationResult(null)
    }

    // Validate mutation
    const validateMutation = useMutation({
        mutationFn: () => tableEntryApi.validateRows(connectionId, schema, table, rows),
        onSuccess: (result) => {
            setValidationResult(result)
        }
    })

    // Insert mutation
    const insertMutation = useMutation({
        mutationFn: () => tableEntryApi.insertRows(connectionId, schema, table, rows, insertMode),
        onSuccess: (result) => {
            if (result.success) {
                alert(`Successfully inserted ${result.rows_inserted} rows!`)
                setRows([getDefaultRow()])
                localStorage.removeItem(storageKey)
                setValidationResult(null)
                queryClient.invalidateQueries({ queryKey: ['table-entry-metadata'] })
            } else {
                alert(`Insert failed: ${result.error_message}`)
            }
        },
        onError: (error: any) => {
            alert(`Insert failed: ${error.response?.data?.detail || error.message}`)
        }
    })

    const handleValidate = () => {
        validateMutation.mutate()
    }

    const handleInsert = () => {
        if (!window.confirm(`You are about to insert ${rows.length} row(s) into ${schema}.${table}. Continue?`)) {
            return
        }
        insertMutation.mutate()
    }

    return (
        <div className="data-entry-grid">
            {/* Grid Controls */}
            <div className="grid-controls">
                <button className="btn btn-outline" onClick={addRow}>
                    ➕ Add Row
                </button>
                <button className="btn btn-outline" onClick={handleValidate} disabled={validateMutation.isPending}>
                    {validateMutation.isPending ? 'Validating...' : '🔍 Validate'}
                </button>
                <button className="btn btn-outline danger-text" onClick={clearAll}>
                    🧹 Clear All
                </button>
                <div className="row-count">
                    {rows.length} row{rows.length !== 1 ? 's' : ''}
                </div>
            </div>

            {/* Validation Results */}
            {validationResult && (
                <ValidationPanel result={validationResult} />
            )}

            {/* Data Grid */}
            <div className="grid-wrapper">
                <table className="entry-table">
                    <thead>
                        <tr>
                            <th className="row-number-header">#</th>
                            {editableColumns.map((col) => (
                                <th key={col.name} className="column-header">
                                    <div className="column-name">
                                        {col.name}
                                        {col.is_primary_key && <span className="pk-badge">PK</span>}
                                        {col.is_foreign_key && <span className="fk-badge">FK</span>}
                                        {!col.nullable && <span className="required-badge">*</span>}
                                    </div>
                                    <div className="column-type">{col.type}</div>
                                </th>
                            ))}
                            <th className="actions-header">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                                <td className="row-number">{rowIndex + 1}</td>
                                {editableColumns.map((col) => (
                                    <td key={col.name} className="data-cell">
                                        <DatatypeCell
                                            column={col}
                                            value={row[col.name]}
                                            onChange={(value) => updateCell(rowIndex, col.name, value)}
                                            error={validationResult?.row_results?.[rowIndex]?.column_errors?.[col.name]}
                                            connectionId={connectionId}
                                            schema={schema}
                                            table={table}
                                        />
                                    </td>
                                ))}
                                <td className="actions-cell">
                                    <button
                                        className="action-btn"
                                        onClick={() => duplicateRow(rowIndex)}
                                        title="Duplicate Row"
                                    >
                                        📋
                                    </button>
                                    <button
                                        className="action-btn"
                                        onClick={() => clearRow(rowIndex)}
                                        title="Clear Row"
                                    >
                                        🔄
                                    </button>
                                    <button
                                        className="action-btn danger"
                                        onClick={() => removeRow(rowIndex)}
                                        title="Delete Row"
                                        disabled={rows.length === 1}
                                    >
                                        🗑️
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Insert Controls */}
            <InsertControls
                mode={insertMode}
                onModeChange={setInsertMode}
                onInsert={handleInsert}
                isInserting={insertMutation.isPending}
                validationResult={validationResult}
            />
        </div>
    )
}
