import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { datasetsApi } from '../services/api'
import { FileUpload } from '../components/FileUpload'
import './FilesPage.css'

interface UploadedFile {
    id: number
    name: string
    file_type: string
    file_size: number
    status: string
    created_at: string
    row_count?: number
}

export const FilesPage: React.FC = () => {
    const [searchQuery, setSearchQuery] = useState('')
    const queryClient = useQueryClient()

    // Fetch all uploaded files (datasets)
    const { data: files = [], isLoading } = useQuery<UploadedFile[]>({
        queryKey: ['uploaded-files'],
        queryFn: async () => {
            const response = await datasetsApi.list()
            return response.data
        }
    })

    // Delete file mutation
    const deleteMutation = useMutation({
        mutationFn: (id: number) => datasetsApi.delete(id),
        onSuccess: () => {
            // Invalidate all dataset-related queries to sync across tabs
            queryClient.invalidateQueries({ queryKey: ['uploaded-files'] })
            queryClient.invalidateQueries({ queryKey: ['datasets'] })
        }
    })

    const handleUploadSuccess = async () => {
        await queryClient.invalidateQueries({ queryKey: ['uploaded-files'] })
        // Force reset and refetch of datasets query
        await queryClient.resetQueries({ queryKey: ['datasets'] })
        await queryClient.refetchQueries({ queryKey: ['datasets'] })
    }

    const handleUpload = async (file: File) => {
        await datasetsApi.upload(file)
    }

    const handleDelete = (id: number, name: string) => {
        if (window.confirm(`Are you sure you want to delete "${name}"?`)) {
            deleteMutation.mutate(id)
        }
    }

    const filteredFiles = files.filter(file =>
        file.name.toLowerCase().includes(searchQuery.toLowerCase())
    )

    const formatFileSize = (bytes: number) => {
        if (!bytes) return 'N/A'
        const kb = bytes / 1024
        if (kb < 1024) return `${kb.toFixed(1)} KB`
        return `${(kb / 1024).toFixed(1)} MB`
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    return (
        <div className="files-page">
            <div className="files-header">
                <div className="files-header-content">
                    <h1>📁 File Manager</h1>
                    <p>Upload, manage, and organize your data files</p>
                </div>
            </div>

            <div className="files-content">
                {/* Upload Section */}
                <div className="upload-section">
                    <FileUpload onUpload={handleUpload} onUploadSuccess={handleUploadSuccess} />
                </div>

                {/* Files List Section */}
                <div className="files-list-section">
                    <div className="files-list-header">
                        <h2>Uploaded Files ({filteredFiles.length})</h2>
                        <div className="search-box">
                            <input
                                type="text"
                                placeholder="Search files..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="loading-state">Loading files...</div>
                    ) : filteredFiles.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-icon">📄</div>
                            <h3>No files found</h3>
                            <p>Upload your first file to get started</p>
                        </div>
                    ) : (
                        <div className="files-grid">
                            {filteredFiles.map((file) => (
                                <div key={file.id} className="file-card">
                                    <div className="file-icon">
                                        {file.file_type === 'xlsx' || file.file_type === 'xls' ? '📊' :
                                            file.file_type === 'csv' ? '📈' :
                                                file.file_type === 'json' ? '📋' : '📄'}
                                    </div>
                                    <div className="file-info">
                                        <h3 className="file-name">{file.name}</h3>
                                        <div className="file-meta">
                                            <span className="file-type">{file.file_type?.toUpperCase()}</span>
                                            <span className="file-size">{formatFileSize(file.file_size)}</span>
                                            {file.row_count && (
                                                <span className="file-rows">{file.row_count} rows</span>
                                            )}
                                        </div>
                                        <div className="file-date">
                                            Uploaded {formatDate(file.created_at)}
                                        </div>
                                        <div className={`file-status status-${file.status}`}>
                                            {file.status}
                                        </div>
                                    </div>
                                    <div className="file-actions">
                                        <button
                                            className="btn-delete"
                                            onClick={() => handleDelete(file.id, file.name)}
                                            disabled={deleteMutation.isPending}
                                        >
                                            🗑️ Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
