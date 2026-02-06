/**
 * Insert Controls Component
 * Controls for insert mode selection and execution
 */
import React from 'react'
import './InsertControls.css'

interface InsertControlsProps {
    mode: 'transaction' | 'row-by-row'
    onModeChange: (mode: 'transaction' | 'row-by-row') => void
    onInsert: () => void
    isInserting: boolean
    validationResult: any
}

export const InsertControls: React.FC<InsertControlsProps> = ({
    mode,
    onModeChange,
    onInsert,
    isInserting,
    validationResult
}) => {
    const canInsert = validationResult?.is_valid === true

    return (
        <div className="insert-controls">
            <div className="insert-mode-selector">
                <label>Insert Mode:</label>
                <div className="mode-options">
                    <label className="mode-option">
                        <input
                            type="radio"
                            name="insert-mode"
                            value="transaction"
                            checked={mode === 'transaction'}
                            onChange={() => onModeChange('transaction')}
                        />
                        <span className="mode-label">
                            <strong>Transaction</strong>
                            <small>All-or-nothing (recommended)</small>
                        </span>
                    </label>
                    <label className="mode-option">
                        <input
                            type="radio"
                            name="insert-mode"
                            value="row-by-row"
                            checked={mode === 'row-by-row'}
                            onChange={() => onModeChange('row-by-row')}
                        />
                        <span className="mode-label">
                            <strong>Row-by-Row</strong>
                            <small>Continue on failure</small>
                        </span>
                    </label>
                </div>
            </div>

            <div className="insert-actions">
                {!canInsert && validationResult && (
                    <div className="insert-warning">
                        ⚠️ Please fix validation errors before inserting
                    </div>
                )}
                <button
                    className="btn btn-primary btn-large"
                    onClick={onInsert}
                    disabled={isInserting || !canInsert}
                >
                    {isInserting ? '⏳ Inserting...' : '✅ Insert Rows'}
                </button>
            </div>
        </div>
    )
}
