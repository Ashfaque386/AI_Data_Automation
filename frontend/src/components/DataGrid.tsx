import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { datasetsApi } from '../services/api'
import './DataGrid.css'

interface Column {
    name: string
    data_type: string
}

interface DataGridProps {
    datasetId: number
}

export const DataGrid: React.FC<DataGridProps> = ({ datasetId }) => {
    const [page, setPage] = useState(1)
    const [pageSize] = useState(100)

    const { data, isLoading, error } = useQuery({
        queryKey: ['dataset-data', datasetId, page],
        queryFn: async () => {
            const response = await datasetsApi.getData(datasetId, {
                page,
                page_size: pageSize,
            })
            return response.data
        },
    })

    if (isLoading) return <div className="data-grid-loading">Loading data...</div>
    if (error) return <div className="data-grid-error">Error loading data</div>
    if (!data) return null

    return (
        <div className="data-grid-container">
            <div className="data-grid-header">
                <div className="data-grid-info">
                    <span>Total: {data.total_rows.toLocaleString()} rows</span>
                    <span>Page {page} of {data.total_pages}</span>
                </div>
                <div className="data-grid-actions">
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
                            <th className="row-number">#</th>
                            {data.columns.map((col: Column) => (
                                <th key={col.name}>
                                    <div className="column-header">
                                        <span className="column-name">{col.name}</span>
                                        <span className="column-type">{col.data_type}</span>
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.data.map((row: any, idx: number) => (
                            <tr key={idx}>
                                <td className="row-number">{(page - 1) * pageSize + idx + 1}</td>
                                {data.columns.map((col: Column) => (
                                    <td key={col.name}>
                                        {row[col.name] !== null && row[col.name] !== undefined
                                            ? String(row[col.name])
                                            : <span className="null-value">NULL</span>
                                        }
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
