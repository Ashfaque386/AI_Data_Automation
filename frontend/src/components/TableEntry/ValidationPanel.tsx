/**
 * Validation Panel Component
 * Displays validation results and errors
 */
import React from 'react'
import './ValidationPanel.css'

interface ValidationPanelProps {
    result: {
        is_valid: boolean
        total_rows: number
        valid_rows: number
        invalid_rows: number
        row_results: Array<{
            row_index: number
            is_valid: boolean
            errors: string[]
            column_errors: Record<string, string>
        }>
    }
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({ result }) => {
    if (result.is_valid) {
        return (
            <div className="validation-panel success">
                <div className="panel-icon">✅</div>
                <div className="panel-content">
                    <h4>Validation Passed</h4>
                    <p>All {result.total_rows} row(s) are valid and ready to insert.</p>
                </div>
            </div>
        )
    }

    return (
        <div className="validation-panel error">
            <div className="panel-icon">⚠️</div>
            <div className="panel-content">
                <h4>Validation Failed</h4>
                <p>
                    {result.invalid_rows} of {result.total_rows} row(s) have errors.
                    Please fix the highlighted cells before inserting.
                </p>
                <div className="error-list">
                    {result.row_results
                        .filter((row) => !row.is_valid)
                        .map((row) => (
                            <div key={row.row_index} className="error-item">
                                <strong>Row {row.row_index + 1}:</strong>
                                <ul>
                                    {row.errors.map((error, idx) => (
                                        <li key={idx}>{error}</li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                </div>
            </div>
        </div>
    )
}
