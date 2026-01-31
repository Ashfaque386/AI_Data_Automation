import React, { useState, useEffect } from 'react'
import './FormulaEditor.css'

interface FormulaEditorProps {
    isOpen: boolean
    onClose: () => void
    onSave: (columnName: string, formula: string, dataType: string) => Promise<void>
    existingFormula?: {
        columnName: string
        formula: string
        dataType: string
    }
    availableColumns: string[]
    datasetId: number
}

interface ValidationResult {
    is_valid: boolean
    error?: string
    dependencies: string[]
    functions: string[]
}

const EXCEL_FUNCTIONS = [
    { name: 'SUM', description: 'Sum all values', example: '=SUM([Amount])' },
    { name: 'AVERAGE', description: 'Calculate average', example: '=AVERAGE([Price])' },
    { name: 'MIN', description: 'Minimum value', example: '=MIN([Quantity])' },
    { name: 'MAX', description: 'Maximum value', example: '=MAX([Total])' },
    { name: 'COUNT', description: 'Count non-empty values', example: '=COUNT([Status])' },
    { name: 'IF', description: 'Conditional logic', example: '=IF([Amount]>100, "High", "Low")' },
    { name: 'CONCAT', description: 'Concatenate text', example: '=CONCAT([First], " ", [Last])' },
    { name: 'UPPER', description: 'Convert to uppercase', example: '=UPPER([Name])' },
    { name: 'LOWER', description: 'Convert to lowercase', example: '=LOWER([Email])' },
    { name: 'ROUND', description: 'Round number', example: '=ROUND([Price], 2)' },
    { name: 'ABS', description: 'Absolute value', example: '=ABS([Difference])' },
    { name: 'LEN', description: 'String length', example: '=LEN([Description])' },
]

export const FormulaEditor: React.FC<FormulaEditorProps> = ({
    isOpen,
    onClose,
    onSave,
    existingFormula,
    availableColumns,
    datasetId
}) => {
    const [columnName, setColumnName] = useState('')
    const [formula, setFormula] = useState('=')
    const [dataType, setDataType] = useState('string')
    const [validation, setValidation] = useState<ValidationResult | null>(null)
    const [isValidating, setIsValidating] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [showAutocomplete, setShowAutocomplete] = useState(false)
    const [autocompleteFilter, setAutocompleteFilter] = useState('')
    const [cursorPosition, setCursorPosition] = useState(1)

    useEffect(() => {
        if (existingFormula) {
            setColumnName(existingFormula.columnName)
            setFormula(existingFormula.formula)
            setDataType(existingFormula.dataType)
        } else {
            setColumnName('')
            setFormula('=')
            setDataType('string')
        }
        setValidation(null)
    }, [existingFormula, isOpen])

    // Auto-validate formula on change (debounced)
    useEffect(() => {
        if (formula.length <= 1) {
            setValidation(null)
            return
        }

        const timer = setTimeout(() => {
            validateFormula()
        }, 500)

        return () => clearTimeout(timer)
    }, [formula])

    const validateFormula = async () => {
        if (formula.length <= 1) return

        setIsValidating(true)
        try {
            const response = await fetch(`/api/datasets/${datasetId}/formulas/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ formula })
            })

            const result = await response.json()
            setValidation(result)
        } catch (error) {
            console.error('Validation error:', error)
        } finally {
            setIsValidating(false)
        }
    }

    const handleFormulaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newFormula = e.target.value
        setFormula(newFormula)
        setCursorPosition(e.target.selectionStart || 0)

        // Check if we should show autocomplete
        const textBeforeCursor = newFormula.substring(0, e.target.selectionStart)
        const match = textBeforeCursor.match(/\[([^\]]*?)$/
        )

        if (match) {
            setAutocompleteFilter(match[1])
            setShowAutocomplete(true)
        } else {
            setShowAutocomplete(false)
        }
    }

    const insertColumn = (column: string) => {
        const before = formula.substring(0, cursorPosition)
        const after = formula.substring(cursorPosition)

        // Remove partial column reference if exists
        const cleanBefore = before.replace(/\[[^\]]*$/, '')

        setFormula(`${cleanBefore}[${column}]${after}`)
        setShowAutocomplete(false)
    }

    const insertFunction = (funcName: string) => {
        const before = formula.substring(0, cursorPosition)
        const after = formula.substring(cursorPosition)
        setFormula(`${before}${funcName}()${after}`)
    }

    const handleSave = async () => {
        if (!columnName.trim()) {
            alert('Please enter a column name')
            return
        }

        if (!formula || formula === '=') {
            alert('Please enter a formula')
            return
        }

        if (validation && !validation.is_valid) {
            alert(`Invalid formula: ${validation.error}`)
            return
        }

        setIsSaving(true)
        try {
            await onSave(columnName, formula, dataType)
            onClose()
        } catch (error: any) {
            alert(`Failed to save formula: ${error.message}`)
        } finally {
            setIsSaving(false)
        }
    }

    if (!isOpen) return null

    const filteredColumns = availableColumns.filter(col =>
        col.toLowerCase().includes(autocompleteFilter.toLowerCase())
    )

    return (
        <div className="formula-editor-overlay" onClick={onClose}>
            <div className="formula-editor-modal" onClick={e => e.stopPropagation()}>
                <div className="formula-editor-header">
                    <h2>{existingFormula ? 'Edit Formula' : 'Add Formula Column'}</h2>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <div className="formula-editor-body">
                    {/* Column Name */}
                    <div className="form-group">
                        <label>Column Name</label>
                        <input
                            type="text"
                            value={columnName}
                            onChange={e => setColumnName(e.target.value)}
                            placeholder="e.g., Total_Amount"
                            disabled={!!existingFormula}
                            className="column-name-input"
                        />
                    </div>

                    {/* Formula Input */}
                    <div className="form-group">
                        <label>
                            Formula
                            {isValidating && <span className="validating-indicator">Validating...</span>}
                        </label>
                        <div className="formula-input-wrapper">
                            <textarea
                                value={formula}
                                onChange={handleFormulaChange}
                                placeholder="=SUM([Amount])"
                                className={`formula-input ${validation?.is_valid === false ? 'error' : validation?.is_valid ? 'valid' : ''}`}
                                rows={4}
                            />
                            {showAutocomplete && filteredColumns.length > 0 && (
                                <div className="autocomplete-dropdown">
                                    {filteredColumns.slice(0, 10).map(col => (
                                        <div
                                            key={col}
                                            className="autocomplete-item"
                                            onClick={() => insertColumn(col)}
                                        >
                                            <span className="column-icon">📊</span>
                                            {col}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        {validation && !validation.is_valid && (
                            <div className="validation-error">
                                ⚠️ {validation.error}
                            </div>
                        )}
                        {validation && validation.is_valid && (
                            <div className="validation-success">
                                ✓ Valid formula
                                {validation.dependencies.length > 0 && (
                                    <span className="dependencies">
                                        {' '}• Depends on: {validation.dependencies.join(', ')}
                                    </span>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Data Type */}
                    <div className="form-group">
                        <label>Result Data Type</label>
                        <select value={dataType} onChange={e => setDataType(e.target.value)} className="data-type-select">
                            <option value="string">Text</option>
                            <option value="integer">Integer</option>
                            <option value="float">Decimal</option>
                            <option value="boolean">Boolean</option>
                            <option value="date">Date</option>
                        </select>
                    </div>

                    {/* Function Reference */}
                    <div className="function-reference">
                        <h3>Available Functions</h3>
                        <div className="function-grid">
                            {EXCEL_FUNCTIONS.map(func => (
                                <div key={func.name} className="function-card" onClick={() => insertFunction(func.name)}>
                                    <div className="function-name">{func.name}</div>
                                    <div className="function-desc">{func.description}</div>
                                    <div className="function-example">{func.example}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Quick Insert Columns */}
                    <div className="column-reference">
                        <h3>Insert Column</h3>
                        <div className="column-chips">
                            {availableColumns.slice(0, 20).map(col => (
                                <button
                                    key={col}
                                    className="column-chip"
                                    onClick={() => insertColumn(col)}
                                >
                                    {col}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="formula-editor-footer">
                    <button className="btn btn-outline" onClick={onClose} disabled={isSaving}>
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={isSaving || (validation && !validation.is_valid)}
                    >
                        {isSaving ? 'Saving...' : existingFormula ? 'Update Formula' : 'Add Column'}
                    </button>
                </div>
            </div>
        </div>
    )
}
