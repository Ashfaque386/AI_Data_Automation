import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { datasetsApi } from '../services/api'
import { editOperationsApi } from '../services/editOperationsApi'
import { DataGrid } from '../components/DataGrid'
import './DatasetsPage.css'

export const DatasetsPage: React.FC = () => {
    const queryClient = useQueryClient()
    const navigate = useNavigate()
    const [selectedDataset, setSelectedDataset] = useState<number | null>(null)
    const [searchTerm, setSearchTerm] = useState('')
    const [editMode, setEditMode] = useState(false)
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [lockStatus, setLockStatus] = useState<any>(null)

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
            // Invalidate all dataset-related queries to sync across tabs
            queryClient.invalidateQueries({ queryKey: ['datasets'] })
            queryClient.invalidateQueries({ queryKey: ['uploaded-files'] })
            if (selectedDataset) setSelectedDataset(null)
        }
    })

    const filteredDatasets = datasets?.filter((d: any) =>
        d.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) || []

    const selectedDatasetData = datasets?.find((d: any) => d.id === selectedDataset)

    // Check lock status when dataset is selected
    React.useEffect(() => {
        if (selectedDataset && !editMode) {
            editOperationsApi.getLockStatus(selectedDataset)
                .then(status => setLockStatus(status))
                .catch(() => setLockStatus(null))
        }
    }, [selectedDataset, editMode])

    const handleClearLock = async () => {
        if (!selectedDataset) return

        if (window.confirm('Force unlock this dataset? This will clear any active edit session and enter edit mode.')) {
            try {
                console.log('Clearing lock for dataset:', selectedDataset)
                const result = await editOperationsApi.forceUnlock(selectedDataset)
                console.log('Force unlock result:', result)

                // Verify lock is cleared
                const verifyStatus = await editOperationsApi.getLockStatus(selectedDataset)
                console.log('Lock status after clear:', verifyStatus)

                if (verifyStatus.locked) {
                    alert('Lock could not be cleared. Please try again.')
                    setLockStatus(verifyStatus)
                    return
                }

                // Lock is cleared, now enter edit mode
                try {
                    const lockResponse = await editOperationsApi.lockDataset(selectedDataset, 30)
                    console.log('New lock acquired:', lockResponse)
                    setSessionId(lockResponse.session_id)
                    setEditMode(true)
                    setLockStatus(null)
                } catch (lockError: any) {
                    console.error('Failed to acquire new lock:', lockError)
                    alert(`Lock cleared but failed to enter edit mode: ${lockError.response?.data?.detail || lockError.message}`)
                    setLockStatus(null)
                }
            } catch (error: any) {
                console.error('Failed to clear lock:', error)
                alert(`Failed to clear lock: ${error.response?.data?.detail || error.message}`)
            }
        }
    }

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
                                {lockStatus?.locked && !editMode && (
                                    <>
                                        <div className="lock-status-indicator">
                                            🔒 Locked by User {lockStatus.user_id}
                                        </div>
                                        <button
                                            className="btn btn-warning"
                                            onClick={handleClearLock}
                                            title="Force unlock this dataset"
                                        >
                                            🔓 Clear Lock
                                        </button>
                                    </>
                                )}
                                {editMode && (
                                    <>
                                        <button
                                            className="btn btn-success"
                                            onClick={async () => {
                                                if (window.confirm('Commit all changes? This will make them permanent.')) {
                                                    try {
                                                        if (selectedDataset && sessionId) {
                                                            const result = await editOperationsApi.commitChanges(selectedDataset, sessionId)
                                                            alert(`Successfully committed ${result.changes_committed} changes!`)
                                                            setEditMode(false)
                                                            setSessionId(null)
                                                            queryClient.invalidateQueries({ queryKey: ['datasets'] })
                                                            queryClient.invalidateQueries({ queryKey: ['dataset-data', selectedDataset] })
                                                        }
                                                    } catch (error: any) {
                                                        alert(`Failed to commit changes: ${error.response?.data?.detail || error.message}`)
                                                    }
                                                }
                                            }}
                                            title="Commit changes"
                                        >
                                            ✅ Commit
                                        </button>
                                        <button
                                            className="btn btn-outline-danger"
                                            onClick={async () => {
                                                if (window.confirm('Discard all changes? This cannot be undone.')) {
                                                    try {
                                                        if (selectedDataset && sessionId) {
                                                            const result = await editOperationsApi.discardChanges(selectedDataset, sessionId)
                                                            alert(`Discarded ${result.changes_discarded} changes`)
                                                            setEditMode(false)
                                                            setSessionId(null)
                                                            queryClient.invalidateQueries({ queryKey: ['datasets'] })
                                                            queryClient.invalidateQueries({ queryKey: ['dataset-data', selectedDataset] })
                                                        }
                                                    } catch (error: any) {
                                                        alert(`Failed to discard changes: ${error.response?.data?.detail || error.message}`)
                                                    }
                                                }
                                            }}
                                            title="Discard all changes"
                                        >
                                            🗑 Discard
                                        </button>
                                    </>
                                )}
                                <button
                                    className={`btn ${editMode ? 'btn-outline' : 'btn-primary'}`}
                                    onClick={async () => {
                                        if (editMode) {
                                            if (window.confirm('Exit edit mode? Any unsaved changes will be lost.')) {
                                                try {
                                                    if (selectedDataset && sessionId) {
                                                        await editOperationsApi.unlockDataset(selectedDataset, sessionId)
                                                    }
                                                    setEditMode(false)
                                                    setSessionId(null)
                                                } catch (error: any) {
                                                    alert(`Failed to exit edit mode: ${error.response?.data?.detail || error.message}`)
                                                }
                                            }
                                        } else {
                                            try {
                                                if (selectedDataset) {
                                                    const lockResponse = await editOperationsApi.lockDataset(selectedDataset, 30)
                                                    setSessionId(lockResponse.session_id)
                                                    setEditMode(true)
                                                    setLockStatus(null) // Clear lock status when entering edit mode
                                                }
                                            } catch (error: any) {
                                                if (error.response?.status === 409) {
                                                    // Refresh lock status on conflict
                                                    const status = await editOperationsApi.getLockStatus(selectedDataset)
                                                    setLockStatus(status)
                                                    alert('Dataset is currently locked by another user. Use the "Clear Lock" button if needed.')
                                                } else {
                                                    alert(`Failed to enter edit mode: ${error.response?.data?.detail || error.message}`)
                                                }
                                            }
                                        }
                                    }}
                                    title={editMode ? 'Exit edit mode' : 'Enter edit mode'}
                                >
                                    {editMode ? '👁️ View' : '✏️ Edit'}
                                </button>
                                <button
                                    className="btn btn-danger"
                                    onClick={() => {
                                        if (window.confirm('Are you sure you want to delete this dataset?')) {
                                            deleteMutation.mutate(selectedDataset)
                                        }
                                    }}
                                    disabled={editMode}
                                    title={editMode ? 'Cannot delete while in edit mode' : 'Delete dataset'}
                                >
                                    🗑 Delete
                                </button>
                            </div>
                        </div>
                        {editMode && (
                            <div className="edit-mode-banner">
                                <span className="banner-icon">⚠️</span>
                                <span className="banner-text">
                                    <strong>Edit Mode Active:</strong> You are now editing live data. All changes are tracked and auditable.
                                </span>
                            </div>
                        )}
                        <div className="grid-wrapper">
                            <DataGrid datasetId={selectedDataset} editMode={editMode} sessionId={sessionId} />
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
