import React, { useState, useEffect } from 'react';
import { jobsApi } from '../../services/jobsApi';
import './BackupWizard.css';

interface BackupWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onBackupCreated: () => void;
}

interface ConnectionProfile {
    id: number;
    name: string;
    db_type: string;
}

export const BackupWizard: React.FC<BackupWizardProps> = ({ isOpen, onClose, onBackupCreated }) => {
    const [step, setStep] = useState(1);
    const [connections, setConnections] = useState<ConnectionProfile[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Step 1: Connection selection
    const [connectionId, setConnectionId] = useState<number | null>(null);

    // Step 2: Backup type
    const [backupType, setBackupType] = useState<'full' | 'schema' | 'data'>('full');

    // Step 3: Options
    const [compression, setCompression] = useState(true);
    const [format, setFormat] = useState<'custom' | 'tar' | 'plain'>('custom');
    const [retentionDays, setRetentionDays] = useState(30);


    useEffect(() => {
        if (isOpen) {
            fetchConnections();
        }
    }, [isOpen]);

    const fetchConnections = async () => {
        setLoading(true);
        try {
            const data = await jobsApi.getConnections();
            setConnections(data);
            if (data.length > 0 && !connectionId) {
                setConnectionId(data[0].id);
            }
        } catch (err: any) {
            console.error('Failed to fetch connections:', err);
            setError('Failed to load database connections. Please check your network or try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleNext = () => {
        if (step === 1 && !connectionId) {
            setError('Please select a database connection');
            return;
        }
        setError(null);
        setStep(step + 1);
    };

    const handleBack = () => {
        setError(null);
        setStep(step - 1);
    };

    const handleExecuteBackup = async () => {
        if (!connectionId) {
            setError('Please select a connection');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const selectedConnection = connections.find(c => c.id === connectionId);
            if (!selectedConnection) {
                throw new Error('Connection not found');
            }

            // Extract database name from connection
            const databaseName = selectedConnection.name; // Simplified - should parse from connection string

            await jobsApi.quickBackup({
                connection_id: connectionId,
                database_name: databaseName,
                backup_type: backupType,
                compression_enabled: compression,
                retention_days: retentionDays,
                format: format
            });

            onBackupCreated();
            handleClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Backup failed');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setConnectionId(null);
        setBackupType('full');
        setCompression(true);
        setFormat('custom');
        setRetentionDays(30);

        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="wizard-overlay" onClick={handleClose}>
            <div className="wizard-content" onClick={(e) => e.stopPropagation()}>
                <div className="wizard-header">
                    <h2>Database Backup Wizard</h2>
                    <button className="close-button" onClick={handleClose}>×</button>
                </div>

                <div className="wizard-progress">
                    <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
                        <div className="step-number">1</div>
                        <div className="step-label">Connection</div>
                    </div>
                    <div className={`progress-line ${step >= 2 ? 'active' : ''}`}></div>
                    <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
                        <div className="step-number">2</div>
                        <div className="step-label">Backup Type</div>
                    </div>
                    <div className={`progress-line ${step >= 3 ? 'active' : ''}`}></div>
                    <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
                        <div className="step-number">3</div>
                        <div className="step-label">Options</div>
                    </div>
                    <div className={`progress-line ${step >= 4 ? 'active' : ''}`}></div>
                    <div className={`progress-step ${step >= 4 ? 'active' : ''}`}>
                        <div className="step-number">4</div>
                        <div className="step-label">Confirm</div>
                    </div>
                </div>

                <div className="wizard-body">
                    {/* Step 1: Select Connection */}
                    {step === 1 && (
                        <div className="wizard-step">
                            <h3>Select Database Connection</h3>
                            <p className="step-description">
                                Choose the database you want to backup
                            </p>
                            <div className="connection-list">
                                {connections.map((conn) => (
                                    <div
                                        key={conn.id}
                                        className={`connection-card ${connectionId === conn.id ? 'selected' : ''}`}
                                        onClick={() => setConnectionId(conn.id)}
                                    >
                                        <div className="connection-icon">
                                            {conn.db_type === 'postgresql' ? '🐘' : '🗄️'}
                                        </div>
                                        <div className="connection-info">
                                            <div className="connection-name">{conn.name}</div>
                                            <div className="connection-type">{conn.db_type}</div>
                                        </div>
                                        {connectionId === conn.id && (
                                            <div className="selected-indicator">✓</div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Backup Type */}
                    {step === 2 && (
                        <div className="wizard-step">
                            <h3>Choose Backup Type</h3>
                            <p className="step-description">
                                Select what to include in the backup
                            </p>
                            <div className="backup-types">
                                <div
                                    className={`backup-type-card ${backupType === 'full' ? 'selected' : ''}`}
                                    onClick={() => setBackupType('full')}
                                >
                                    <div className="type-icon">📦</div>
                                    <div className="type-name">Full Backup</div>
                                    <div className="type-description">
                                        Complete database including schema and data
                                    </div>
                                </div>
                                <div
                                    className={`backup-type-card ${backupType === 'schema' ? 'selected' : ''}`}
                                    onClick={() => setBackupType('schema')}
                                >
                                    <div className="type-icon">🏗️</div>
                                    <div className="type-name">Schema Only</div>
                                    <div className="type-description">
                                        Database structure without data
                                    </div>
                                </div>
                                <div
                                    className={`backup-type-card ${backupType === 'data' ? 'selected' : ''}`}
                                    onClick={() => setBackupType('data')}
                                >
                                    <div className="type-icon">📊</div>
                                    <div className="type-name">Data Only</div>
                                    <div className="type-description">
                                        Table data without schema
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 3: Options */}
                    {step === 3 && (
                        <div className="wizard-step">
                            <h3>Backup Options</h3>
                            <p className="step-description">
                                Configure backup settings
                            </p>
                            <div className="options-form">
                                <div className="option-group">
                                    <label className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={compression}
                                            onChange={(e) => setCompression(e.target.checked)}
                                        />
                                        <span>Enable Compression</span>
                                    </label>
                                    <small>Reduce backup file size (recommended)</small>
                                </div>

                                <div className="option-group">
                                    <label>Backup Format</label>
                                    <select value={format} onChange={(e) => setFormat(e.target.value as any)}>
                                        <option value="custom">Custom (pg_dump)</option>
                                        <option value="tar">TAR Archive</option>
                                        <option value="plain">Plain SQL</option>
                                    </select>
                                    <small>Custom format is recommended for flexibility</small>
                                </div>

                                <div className="option-group">
                                    <label>Retention Period (days)</label>
                                    <input
                                        type="number"
                                        value={retentionDays}
                                        onChange={(e) => setRetentionDays(Number(e.target.value))}
                                        min="1"
                                        max="365"
                                    />
                                    <small>Backups older than this will be automatically deleted</small>
                                </div>

                            </div>
                        </div>
                    )}

                    {/* Step 4: Confirm */}
                    {step === 4 && (
                        <div className="wizard-step">
                            <h3>Confirm Backup</h3>
                            <p className="step-description">
                                Review your backup configuration
                            </p>
                            <div className="confirmation-summary">
                                <div className="summary-item">
                                    <span className="summary-label">Database:</span>
                                    <span className="summary-value">
                                        {connections.find(c => c.id === connectionId)?.name}
                                    </span>
                                </div>
                                <div className="summary-item">
                                    <span className="summary-label">Backup Type:</span>
                                    <span className="summary-value">{backupType.toUpperCase()}</span>
                                </div>
                                <div className="summary-item">
                                    <span className="summary-label">Compression:</span>
                                    <span className="summary-value">{compression ? 'Enabled' : 'Disabled'}</span>
                                </div>
                                <div className="summary-item">
                                    <span className="summary-label">Format:</span>
                                    <span className="summary-value">{format.toUpperCase()}</span>
                                </div>
                                <div className="summary-item">
                                    <span className="summary-label">Retention:</span>
                                    <span className="summary-value">{retentionDays} days</span>
                                </div>

                            </div>
                        </div>
                    )}
                </div>

                {error && (
                    <div className="wizard-error">
                        {error}
                    </div>
                )}

                <div className="wizard-footer">
                    {step > 1 && (
                        <button
                            type="button"
                            onClick={handleBack}
                            className="btn-secondary"
                            disabled={loading}
                        >
                            Back
                        </button>
                    )}
                    <div className="footer-spacer"></div>
                    <button
                        type="button"
                        onClick={handleClose}
                        className="btn-secondary"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    {step < 4 ? (
                        <button
                            type="button"
                            onClick={handleNext}
                            className="btn-primary"
                        >
                            Next
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={handleExecuteBackup}
                            className="btn-primary"
                            disabled={loading}
                        >
                            {loading ? 'Creating Backup...' : 'Start Backup'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};
