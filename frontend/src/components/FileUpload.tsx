import React, { useState, useRef } from 'react'
import './FileUpload.css'

interface FileUploadProps {
    onUpload: (file: File) => Promise<void>
    onUploadSuccess?: () => void
    accept?: string
    maxSize?: number // In MB
}

export const FileUpload: React.FC<FileUploadProps> = ({
    onUpload,
    onUploadSuccess,
    accept = '.xlsx,.xls,.csv,.json',
    maxSize = 50
}) => {
    const [isDragging, setIsDragging] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [progress, setProgress] = useState(0)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = () => {
        setIsDragging(false)
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files[0]
        validateAndUpload(file)
    }

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) validateAndUpload(file)
    }

    const validateAndUpload = async (file: File) => {
        setError(null)

        // Basic validation
        const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
        if (!accept.split(',').includes(fileExt)) {
            setError(`Invalid file type. Supported: ${accept}`)
            return
        }

        if (file.size > maxSize * 1024 * 1024) {
            setError(`File too large. Maximum size is ${maxSize}MB`)
            return
        }

        setUploading(true)
        setProgress(0)

        // Simulated progress for better UX
        const interval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 90) {
                    clearInterval(interval)
                    return 90
                }
                return prev + 10
            })
        }, 100)

        try {
            await onUpload(file)
            setProgress(100)
            setTimeout(() => {
                setUploading(false)
                setProgress(0)
                onUploadSuccess?.()
            }, 500)
        } catch (err) {
            setError('Upload failed. Please try again.')
            setUploading(false)
        } finally {
            clearInterval(interval)
        }
    }

    return (
        <div
            className={`file-upload-container ${isDragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !uploading && fileInputRef.current?.click()}
        >
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept={accept}
                style={{ display: 'none' }}
            />

            <div className="upload-content">
                {uploading ? (
                    <div className="upload-progress-state">
                        <div className="progress-spinner"></div>
                        <p>Uploading and processing...</p>
                        <div className="progress-bar-container">
                            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className="upload-icon">📤</div>
                        <h3>Upload Data</h3>
                        <p>Drag and drop your file here, or click to browse</p>
                        <div className="upload-types">
                            <span>CSV</span>
                            <span>Excel</span>
                            <span>JSON</span>
                        </div>
                    </>
                )}
            </div>

            {error && <div className="upload-error">{error}</div>}
        </div>
    )
}
