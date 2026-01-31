import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { datasetsApi } from '../services/api'
import { editOperationsApi } from '../services/editOperationsApi'
import './DataGrid.css'

interface Column {
    name: string
    data_type: string
}

interface DataGridProps {
    datasetId: number
    editMode?: boolean
    sessionId?: string | null
}

export const DataGrid: React.FC<DataGridProps> = ({ datasetId, editMode = false, sessionId = null }) => {
    const queryClient = useQueryClient()
    const [page, setPage] = useState(1)
    const [pageSize] = useState(100)
    const [editingCell, setEditingCell] = useState<{ rowIdx: number; colName: string } | null>(null)
    const [editedValues, setEditedValues] = useState<Map<string, any>>(new Map())
    const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())
    const [sortColumn, setSortColumn] = useState<string | null>(null)
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
    const [showFilters, setShowFilters] = useState(false)
    const [columnFilters, setColumnFilters] = useState<Map<string, string>>(new Map())
    const [undoStack, setUndoStack] = useState<any[]>([])
    const [redoStack, setRedoStack] = useState<any[]>([])

    const { data, isLoading, error } = useQuery({
        queryKey: ['dataset-data', datasetId, page],
        queryFn: async () => {
            const response = await datasetsApi.getData(datasetId, {
                page,
                page_size: pageSize,
            })
            return response.data
        },
        refetchInterval: editMode ? 10000 : false, // Auto-refresh every 10s in edit mode
        staleTime: editMode ? 5000 : 30000, // Data considered stale after 5s in edit mode
    })

    if (isLoading) return <div className="data-grid-loading">Loading data...</div>
    if (error) return <div className="data-grid-error">Error loading data</div>
    if (!data) return null

    return (
        <div className={`data-grid-container ${editMode ? 'edit-mode' : ''}`}>
            <div className="data-grid-header">
                <div className="data-grid-info">
                    <span>Total: {data.total_rows.toLocaleString()} rows</span>
                    <span>Page {page} of {data.total_pages}</span>
                    {editMode && <span className="edit-indicator">✏️ EDIT MODE</span>}
                    {editMode && selectedRows.size > 0 && (
                        <span className="selection-count">{selectedRows.size} row(s) selected</span>
                    )}
                </div>
                <div className="data-grid-actions">
                    {editMode && (
                        <>
                            <button
                                className="btn btn-sm btn-success"
                                onClick={async () => {
                                    if (!sessionId) {
                                        alert('No active edit session')
                                        return
                                    }
                                    try {
                                        await editOperationsApi.addRow(datasetId, sessionId, data.data.length, {})
                                        queryClient.invalidateQueries({ queryKey: ['dataset-data', datasetId] })
                                        alert('Row added successfully!')
                                    } catch (error: any) {
                                        alert(`Failed to add row: ${error.response?.data?.detail || error.message}`)
                                    }
                                }}
                                title="Add new row"
                            >
                                ➕ Add Row
                            </button>
                            <button
                                className="btn btn-sm btn-primary"
                                onClick={() => {
                                    if (selectedRows.size === 0) {
                                        alert('Please select rows to duplicate')
                                        return
                                    }
                                    alert(`Duplicate ${selectedRows.size} row(s): Backend integration pending`)
                                }}
                                disabled={selectedRows.size === 0}
                                title="Duplicate selected rows"
                            >
                                📋 Duplicate
                            </button>
                            <button
                                className="btn btn-sm btn-warning"
                                onClick={() => {
                                    if (selectedRows.size === 0) {
                                        alert('Please select rows to clear')
                                        return
                                    }
                                    if (window.confirm(`Clear data from ${selectedRows.size} selected row(s)?`)) {
                                        alert('Clear Row Data: Backend integration pending')
                                    }
                                }}
                                disabled={selectedRows.size === 0}
                                title="Clear data from selected rows"
                            >
                                🧹 Clear Data
                            </button>
                            <button
                                className="btn btn-sm"
                                onClick={() => {
                                    if (selectedRows.size !== 1) {
                                        alert('Please select exactly one row to move')
                                        return
                                    }
                                    alert('Move Up: Backend integration pending')
                                }}
                                disabled={selectedRows.size !== 1}
                                title="Move selected row up"
                            >
                                ⬆️
                            </button>
                            <button
                                className="btn btn-sm"
                                onClick={() => {
                                    if (selectedRows.size !== 1) {
                                        alert('Please select exactly one row to move')
                                        return
                                    }
                                    alert('Move Down: Backend integration pending')
                                }}
                                disabled={selectedRows.size !== 1}
                                title="Move selected row down"
                            >
                                ⬇️
                            </button>
                            <button
                                className="btn btn-sm btn-danger"
                                onClick={async () => {
                                    if (selectedRows.size === 0) {
                                        alert('Please select rows to delete')
                                        return
                                    }
                                    if (!sessionId) {
                                        alert('No active edit session')
                                        return
                                    }
                                    if (window.confirm(`Delete ${selectedRows.size} selected row(s)?`)) {
                                        try {
                                            await editOperationsApi.deleteRows(datasetId, sessionId, Array.from(selectedRows))
                                            queryClient.invalidateQueries({ queryKey: ['dataset-data', datasetId] })
                                            alert(`Deleted ${selectedRows.size} row(s) successfully!`)
                                            setSelectedRows(new Set())
                                        } catch (error: any) {
                                            alert(`Failed to delete rows: ${error.response?.data?.detail || error.message}`)
                                        }
                                    }
                                }}
                                disabled={selectedRows.size === 0}
                                title="Delete selected rows"
                            >
                                🗑 Delete
                            </button>
                            {selectedRows.size > 0 && (
                                <button
                                    className="btn btn-sm"
                                    onClick={() => setSelectedRows(new Set())}
                                    title="Clear selection"
                                >
                                    ✖ Clear Selection
                                </button>
                            )}
                        </>
                    )}
                    {editMode && (
                        <>
                            <button
                                className="btn btn-sm"
                                onClick={() => {
                                    alert('Undo: Backend integration pending')
                                }}
                                disabled={undoStack.length === 0}
                                title="Undo last change"
                            >
                                ↶ Undo
                            </button>
                            <button
                                className="btn btn-sm"
                                onClick={() => {
                                    alert('Redo: Backend integration pending')
                                }}
                                disabled={redoStack.length === 0}
                                title="Redo last undone change"
                            >
                                ↷ Redo
                            </button>
                        </>
                    )}
                    {editMode && (
                        <button
                            className="btn btn-sm btn-success"
                            onClick={async () => {
                                if (!sessionId) {
                                    alert('No active edit session')
                                    return
                                }
                                const columnName = prompt('Enter column name:')
                                if (columnName) {
                                    const dataType = prompt('Enter data type (string/integer/float/date):', 'string')
                                    try {
                                        await editOperationsApi.addColumn(datasetId, sessionId, columnName, dataType || 'string')
                                        queryClient.invalidateQueries({ queryKey: ['dataset-data', datasetId] })
                                        alert('Column added successfully!')
                                    } catch (error: any) {
                                        alert(`Failed to add column: ${error.response?.data?.detail || error.message}`)
                                    }
                                }
                            }}
                            title="Add new column"
                        >
                            ➕ Add Column
                        </button>
                    )}
                    {editMode && selectedRows.size > 0 && (
                        <button
                            className="btn btn-sm btn-primary"
                            onClick={() => {
                                const value = prompt(`Enter value to apply to ${selectedRows.size} selected row(s):`)
                                if (value !== null) {
                                    alert(`Bulk Edit: Backend integration pending`)
                                }
                            }}
                            title="Bulk edit selected rows"
                        >
                            📝 Bulk Edit
                        </button>
                    )}
                    {editMode && (
                        <button
                            className="btn btn-sm"
                            onClick={() => {
                                const find = prompt('Find text:')
                                if (find) {
                                    const replace = prompt('Replace with:')
                                    if (replace !== null) {
                                        alert(`Find & Replace: Backend integration pending`)
                                    }
                                }
                            }}
                            title="Find and replace"
                        >
                            🔍 Find & Replace
                        </button>
                    )}
                    <button
                        className={`btn btn-sm ${showFilters ? 'btn-primary' : ''}`}
                        onClick={() => setShowFilters(!showFilters)}
                        title="Toggle filters"
                    >
                        🔍 {showFilters ? 'Hide' : 'Show'} Filters
                    </button>
                    {columnFilters.size > 0 && (
                        <button
                            className="btn btn-sm btn-warning"
                            onClick={() => {
                                setColumnFilters(new Map())
                                alert('Filters cleared')
                            }}
                            title="Clear all filters"
                        >
                            ✖ Clear Filters ({columnFilters.size})
                        </button>
                    )}
                    {editMode && (
                        <>
                            <button
                                className="btn btn-sm"
                                onClick={async () => {
                                    if (!sessionId) {
                                        alert('No active edit session')
                                        return
                                    }
                                    try {
                                        const history = await editOperationsApi.getUncommittedChanges(datasetId, sessionId)
                                        if (history.changes.length === 0) {
                                            alert('No changes to undo')
                                            return
                                        }
                                        const lastChange = history.changes[history.changes.length - 1]
                                        // Revert the last change by creating an opposite change
                                        if (lastChange.change_type === 'cell_edit') {
                                            await editOperationsApi.updateCells(datasetId, sessionId, [{
                                                row_index: lastChange.row_index!,
                                                column_name: lastChange.column_name!,
                                                old_value: lastChange.new_value,
                                                new_value: lastChange.old_value
                                            }])
                                        }
                                        queryClient.invalidateQueries({ queryKey: ['dataset-data', datasetId] })
                                        alert('Last change undone')
                                    } catch (error: any) {
                                        alert(`Failed to undo: ${error.response?.data?.detail || error.message}`)
                                    }
                                }}
                                disabled={undoStack.length === 0}
                                title="Undo last change"
                            >
                                ↶ Undo
                            </button>
                            <button
                                className="btn btn-sm"
                                onClick={() => {
                                    if (redoStack.length === 0) {
                                        alert('Nothing to redo')
                                        return
                                    }
                                    alert('Redo: Advanced implementation pending')
                                }}
                                disabled={redoStack.length === 0}
                                title="Redo last undone change"
                            >
                                ↷ Redo
                            </button>
                        </>
                    )}
                    <button
                        className="btn btn-sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                    >
                        ← Previous
                    </button>
                    <button
                        className="btn btn-sm"
                        onClick={() => setPage(p => Math.min(data.total_pages, p + 1))}
                        disabled={page === data.total_pages}
                    >
                        Next →
                    </button>
                </div>
            </div>

            <div className="data-grid-scroll">
                <table className="data-grid-table">
                    <thead>
                        <tr>
                            {editMode && (
                                <th className="row-checkbox">
                                    <input
                                        type="checkbox"
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                const allRows = new Set<number>(data.data.map((_: any, idx: number) => idx))
                                                setSelectedRows(allRows)
                                            } else {
                                                setSelectedRows(new Set())
                                            }
                                        }}
                                        checked={selectedRows.size === data.data.length && data.data.length > 0}
                                    />
                                </th>
                            )}
                            <th className="row-number">#</th>
                            {data.columns.map((col: Column) => (
                                <th
                                    key={col.name}
                                    className="column-header-cell sortable"
                                    onClick={() => {
                                        if (sortColumn === col.name) {
                                            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                                        } else {
                                            setSortColumn(col.name)
                                            setSortDirection('asc')
                                        }
                                    }}
                                >
                                    <div className="column-header">
                                        <div className="column-header-content">
                                            <span className="column-name">
                                                {col.name}
                                                {sortColumn === col.name && (
                                                    <span className="sort-indicator">
                                                        {sortDirection === 'asc' ? ' ↑' : ' ↓'}
                                                    </span>
                                                )}
                                            </span>
                                            <span className="column-type">{col.data_type}</span>
                                        </div>
                                        {showFilters && (
                                            <input
                                                type="text"
                                                className="column-filter-input"
                                                placeholder="Filter..."
                                                value={columnFilters.get(col.name) || ''}
                                                onChange={(e) => {
                                                    const newFilters = new Map(columnFilters)
                                                    if (e.target.value) {
                                                        newFilters.set(col.name, e.target.value)
                                                    } else {
                                                        newFilters.delete(col.name)
                                                    }
                                                    setColumnFilters(newFilters)
                                                }}
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        )}
                                    </div>
                                    {editMode && (
                                        <div className="column-actions">
                                            <button
                                                className="column-action-btn"
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    const newName = prompt('Enter new column name:', col.name)
                                                    if (newName && newName !== col.name) {
                                                        alert(`Rename column "${col.name}" to "${newName}": Backend integration pending`)
                                                    }
                                                }}
                                                title="Rename column"
                                            >
                                                ✏️
                                            </button>
                                            <button
                                                className="column-action-btn"
                                                onClick={async (e) => {
                                                    e.stopPropagation()
                                                    if (!sessionId) {
                                                        alert('No active edit session')
                                                        return
                                                    }
                                                    if (window.confirm(`Delete column "${col.name}"?`)) {
                                                        try {
                                                            await editOperationsApi.deleteColumn(datasetId, sessionId, col.name)
                                                            queryClient.invalidateQueries({ queryKey: ['dataset-data', datasetId] })
                                                            alert('Column deleted successfully!')
                                                        } catch (error: any) {
                                                            alert(`Failed to delete column: ${error.response?.data?.detail || error.message}`)
                                                        }
                                                    }
                                                }}
                                                title="Delete column"
                                            >
                                                🗑
                                            </button>
                                        </div>
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.data.map((row: any, idx: number) => {
                            const rowKey = `${page}-${idx}`
                            const isRowSelected = selectedRows.has(idx)
                            return (
                                <tr key={idx} className={isRowSelected ? 'row-selected' : ''}>
                                    {editMode && (
                                        <td className="row-checkbox">
                                            <input
                                                type="checkbox"
                                                checked={isRowSelected}
                                                onChange={(e) => {
                                                    const newSelected = new Set(selectedRows)
                                                    if (e.target.checked) {
                                                        newSelected.add(idx)
                                                    } else {
                                                        newSelected.delete(idx)
                                                    }
                                                    setSelectedRows(newSelected)
                                                }}
                                            />
                                        </td>
                                    )}
                                    <td className="row-number">{(page - 1) * pageSize + idx + 1}</td>
                                    {data.columns.map((col: Column) => {
                                        const cellKey = `${rowKey}-${col.name}`
                                        const isEditing = editMode && editingCell?.rowIdx === idx && editingCell?.colName === col.name
                                        const isModified = editedValues.has(cellKey)
                                        const value = editedValues.get(cellKey) ?? row[col.name]

                                        return (
                                            <td
                                                key={col.name}
                                                className={`${isModified ? 'cell-modified' : ''}`}
                                                onClick={() => {
                                                    if (editMode && !isEditing) {
                                                        setEditingCell({ rowIdx: idx, colName: col.name })
                                                    }
                                                }}
                                            >
                                                {isEditing ? (
                                                    <input
                                                        type="text"
                                                        className="cell-input"
                                                        defaultValue={value ?? ''}
                                                        autoFocus
                                                        onBlur={async (e) => {
                                                            const newValue = e.target.value
                                                            const oldValue = row[col.name]

                                                            // Update local state
                                                            const newEdited = new Map(editedValues)
                                                            newEdited.set(cellKey, newValue)
                                                            setEditedValues(newEdited)
                                                            setEditingCell(null)

                                                            // Send to backend if session exists
                                                            if (sessionId && newValue !== oldValue) {
                                                                try {
                                                                    await editOperationsApi.updateCells(datasetId, sessionId, [{
                                                                        row_index: idx,
                                                                        column_name: col.name,
                                                                        old_value: oldValue,
                                                                        new_value: newValue
                                                                    }])
                                                                    console.log('Cell update logged to backend')
                                                                } catch (error: any) {
                                                                    console.error('Failed to log cell update:', error)
                                                                    alert(`Failed to save cell: ${error.response?.data?.detail || error.message}`)
                                                                }
                                                            }
                                                        }}
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Enter') {
                                                                e.currentTarget.blur()
                                                            } else if (e.key === 'Escape') {
                                                                setEditingCell(null)
                                                            }
                                                        }}
                                                    />
                                                ) : (
                                                    <div className="cell-content">
                                                        <span className="cell-value">
                                                            {value !== null && value !== undefined
                                                                ? String(value)
                                                                : <span className="null-value">NULL</span>
                                                            }
                                                        </span>
                                                        {isModified && editMode && (
                                                            <button
                                                                className="cell-revert-btn"
                                                                onClick={(e) => {
                                                                    e.stopPropagation()
                                                                    const newEdited = new Map(editedValues)
                                                                    newEdited.delete(cellKey)
                                                                    setEditedValues(newEdited)
                                                                }}
                                                                title="Revert to original value"
                                                            >
                                                                ↶
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </td>
                                        )
                                    })}
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
