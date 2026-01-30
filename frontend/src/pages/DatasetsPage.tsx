import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { datasetsApi } from '../services/api'
import { DataGrid } from '../components/DataGrid'
import './DatasetsPage.css'

export const DatasetsPage: React.FC = () => {
    const queryClient = useQueryClient()
    const navigate = useNavigate()
    const [selectedDataset, setSelectedDataset] = useState<number | null>(null)
    const [searchTerm, setSearchTerm] = useState('')

    const { data: datasets, isLoading } = useQuery({
        queryKey: ['datasets'],
        queryFn: async () => {
            const response = await datasetsApi.list()
            console.log('Fetched datasets:', response.data)
            return response.data
        },
        refetchOnWindowFocus: true,
        refetchOnMount: 'always',
        refetchInterval: 2000,
        staleTime: 0,
    })

    const deleteMutation = useMutation({
        mutationFn: (id: number) => datasetsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['datasets'] })
            if (selectedDataset) setSelectedDataset(null)
        }
    })

    const filteredDatasets = datasets?.filter((d: any) =>
        d.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) || []

    const selectedDatasetData = datasets?.find((d: any) => d.id === selectedDataset)

    return (
        <div className="datasets-page">
            <div className="datasets-sidebar">
                <div className="sidebar-header">
                    <div className="header-top">
                        <h2>Data Sources</h2>
                    </div>
                    <div className="search-box">
                        <span className="search-icon">🔍</span>
                        <input
                            type="text"
                            placeholder="Search datasets..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <div className="datasets-list">
                    {isLoading ? (
                        <div className="loading-state">
                            <div className="skeleton-item"></div>
                            <div className="skeleton-item"></div>
                            <div className="skeleton-item"></div>
                        </div>
                    ) : filteredDatasets.length > 0 ? (
                        filteredDatasets.map((dataset: any) => (
                            <div
                                key={dataset.id}
                                className={`dataset-card ${selectedDataset === dataset.id ? 'active' : ''}`}
                                onClick={() => setSelectedDataset(dataset.id)}
                            >
                                <div className="dataset-icon">
                                    {dataset.file_type === 'csv' ? '📄' : '📊'}
                                </div>
                                <div className="dataset-info">
                                    <div className="dataset-name">{dataset.name}</div>
                                    <div className="dataset-meta">
                                        {dataset.row_count?.toLocaleString()} rows • {dataset.file_type}
                                    </div>
                                </div>
                                <div className={`status-dot ${dataset.status}`}></div>
                            </div>
                        ))
                    ) : (
                        <div className="empty-state">
                            <div className="empty-icon">📂</div>
                            <p>No datasets found</p>
                        </div>
                    )}
                </div>
            </div>

            <div className="datasets-main">
                {selectedDataset ? (
                    <div className="dataset-view">
                        <div className="view-header">
                            <div className="view-header-left">
                                <div className="title-row">
                                    <h1>{selectedDatasetData?.name}</h1>
                                    <span className={`badge badge-${selectedDatasetData?.status === 'ready' ? 'success' : 'warning'}`}>
                                        {selectedDatasetData?.status}
                                    </span>
                                </div>
                                <p className="subtitle">
                                    Uploaded on {new Date(selectedDatasetData?.created_at).toLocaleDateString()} •
                                    {selectedDatasetData?.row_count?.toLocaleString()} total records
                                </p>
                            </div>
                            <div className="view-header-right">
                                <button
                                    className="btn btn-outline-danger"
                                    onClick={() => {
                                        if (window.confirm('Are you sure you want to delete this dataset?')) {
                                            deleteMutation.mutate(selectedDataset)
                                        }
                                    }}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                        <div className="grid-wrapper">
                            <DataGrid datasetId={selectedDataset} />
                        </div>
                    </div>
                ) : (
                    <div className="empty-view">
                        <div className="stunning-hero">
                            <div className="hero-icon">💾</div>
                            <h1>Data Management</h1>
                            <p>Select a dataset from the sidebar to view and analyze your data.</p>
                            <button className="btn btn-primary" onClick={() => navigate('/files')}>
                                Go to Uploaded Files
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
