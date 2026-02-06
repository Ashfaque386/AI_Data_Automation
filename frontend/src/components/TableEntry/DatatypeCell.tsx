/**
 * Datatype Cell Component
 * Smart cell editor that adapts to column datatype
 */
import React from 'react'
import AsyncSelect from 'react-select/async'
import { ColumnMetadata, tableEntryApi } from '../../services/tableEntryApi'
import './DatatypeCell.css'

interface DatatypeCellProps {
    column: ColumnMetadata
    value: any
    onChange: (value: any) => void
    error?: string
    connectionId: number
    schema: string
    table: string
}

export const DatatypeCell: React.FC<DatatypeCellProps> = ({
    column,
    value,
    onChange,
    error,
    connectionId,
    schema,
    table
}) => {
    const baseType = column.type.toUpperCase().split('(')[0]

    // render Foreign Key selector
    if (column.is_foreign_key) {
        return (
            <div className={`datatype-cell ${error ? 'has-error' : ''}`}>
                <AsyncSelect
                    cacheOptions
                    defaultOptions
                    loadOptions={(inputValue) =>
                        tableEntryApi.getForeignKeys(connectionId, schema, table, column.name, inputValue)
                    }
                    onChange={(option: any) => onChange(option ? option.value : null)}
                    value={value ? { label: value.toString(), value: value } : null}
                    placeholder="Select or search..."
                    className="fk-select-container"
                    classNamePrefix="fk-select"
                    styles={{
                        control: (base) => ({
                            ...base,
                            border: 'none',
                            boxShadow: 'none',
                            minHeight: '38px',
                            background: 'transparent'
                        }),
                        menu: (base) => ({
                            ...base,
                            zIndex: 9999
                        })
                    }}
                    menuPortalTarget={document.body}
                />
                {error && <div className="cell-error" title={error}>⚠️</div>}
            </div>
        )
    }

    // Render appropriate input based on datatype
    const renderInput = () => {
        // INTEGER types
        if (['INTEGER', 'INT', 'SMALLINT', 'BIGINT', 'SERIAL', 'BIGSERIAL'].includes(baseType)) {
            return (
                <input
                    type="number"
                    className="cell-input number-input"
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value ? parseInt(e.target.value) : null)}
                    placeholder={column.nullable ? 'NULL' : 'Required'}
                />
            )
        }

        // DECIMAL/NUMERIC types
        if (['DECIMAL', 'NUMERIC', 'REAL', 'DOUBLE', 'FLOAT'].includes(baseType)) {
            return (
                <input
                    type="number"
                    step="any"
                    className="cell-input number-input"
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value ? parseFloat(e.target.value) : null)}
                    placeholder={column.nullable ? 'NULL' : 'Required'}
                />
            )
        }

        // BOOLEAN types
        if (['BOOLEAN', 'BOOL'].includes(baseType)) {
            return (
                <select
                    className="cell-input boolean-input"
                    value={value === null || value === undefined ? '' : value.toString()}
                    onChange={(e) => {
                        if (e.target.value === '') {
                            onChange(null)
                        } else {
                            onChange(e.target.value === 'true')
                        }
                    }}
                >
                    <option value="">NULL</option>
                    <option value="true">True</option>
                    <option value="false">False</option>
                </select>
            )
        }

        // DATE types
        if (baseType === 'DATE') {
            return (
                <input
                    type="date"
                    className="cell-input date-input"
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value || null)}
                />
            )
        }

        // TIMESTAMP/DATETIME types
        if (['TIMESTAMP', 'DATETIME'].includes(baseType)) {
            return (
                <input
                    type="datetime-local"
                    className="cell-input datetime-input"
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value || null)}
                />
            )
        }

        // VARCHAR/TEXT types (default)
        const maxLength = column.type.match(/\((\d+)\)/)?.[1]
        return (
            <div className="text-input-wrapper">
                <input
                    type="text"
                    className="cell-input text-input"
                    value={value ?? ''}
                    onChange={(e) => onChange(e.target.value || null)}
                    placeholder={column.nullable ? 'NULL' : 'Required'}
                    maxLength={maxLength ? parseInt(maxLength) : undefined}
                />
                {maxLength && value && (
                    <span className="char-count">
                        {(value?.toString().length || 0)}/{maxLength}
                    </span>
                )}
            </div>
        )
    }

    return (
        <div className={`datatype-cell ${error ? 'has-error' : ''}`}>
            {renderInput()}
            {error && <div className="cell-error" title={error}>⚠️</div>}
        </div>
    )
}
