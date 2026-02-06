import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './DataImport.css';

interface Dataset {
    id: number;
    name: string;
    file_type: string;
    row_count: number;
    column_count: number;
    status: string;
}

export const DataImport: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(1);
    const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);

    const steps = [
        { number: 1, title: 'Select Dataset', icon: '📊' },
        { number: 2, title: 'Select Target', icon: '🎯' },
        { number: 3, title: 'Map Columns', icon: '🔗' },
        { number: 4, title: 'Preview & Validate', icon: '👁️' },
        { number: 5, title: 'Configure Import', icon: '⚙️' },
        { number: 6, title: 'Execute', icon: '▶️' },
    ];

    const handleDatasetSelect = (dataset: Dataset) => {
        setSelectedDataset(dataset);
        setCurrentStep(2);
    };

    return (
        <div className="data-import-container">
            <div className="import-header">
                <div className="import-header-title">
                    <span className="import-icon">📥</span>
                    <h1>Data Import</h1>
                </div>
                <p className="import-subtitle">
                    Import datasets into your operational database tables
                </p>
            </div>

            {/* Progress Stepper */}
            <div className="import-stepper">
                {steps.map((step) => (
                    <div
                        key={step.number}
                        className={`step ${currentStep === step.number ? 'active' : ''} ${currentStep > step.number ? 'completed' : ''
                            }`}
                    >
                        <div className="step-number">
                            {currentStep > step.number ? '✓' : step.icon}
                        </div>
                        <div className="step-title">{step.title}</div>
                        {step.number < steps.length && <div className="step-connector" />}
                    </div>
                ))}
            </div>

            {/* Step Content */}
            <div className="import-content">
                {currentStep === 1 && (
                    <SelectDatasetStep onNext={handleDatasetSelect} />
                )}
                {currentStep === 2 && (
                    <SelectTargetStep
                        onNext={() => setCurrentStep(3)}
                        onBack={() => setCurrentStep(1)}
                        selectedDataset={selectedDataset}
                    />
                )}
                {currentStep === 3 && (
                    <MapColumnsStep
                        onNext={() => setCurrentStep(4)}
                        onBack={() => setCurrentStep(2)}
                    />
                )}
                {currentStep === 4 && (
                    <PreviewValidateStep
                        onNext={() => setCurrentStep(5)}
                        onBack={() => setCurrentStep(3)}
                    />
                )}
                {currentStep === 5 && (
                    <ConfigureImportStep
                        onNext={() => setCurrentStep(6)}
                        onBack={() => setCurrentStep(4)}
                    />
                )}
                {currentStep === 6 && (
                    <ExecuteStep onBack={() => setCurrentStep(5)} />
                )}
            </div>
        </div>
    );
};

// Step 1: Select Dataset
const SelectDatasetStep: React.FC<{ onNext: (dataset: Dataset) => void }> = ({ onNext }) => {
    const [datasets, setDatasets] = useState<Dataset[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchDatasets = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const response = await axios.get('http://localhost:8000/api/import/datasets', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                setDatasets(response.data.datasets || []);
                setLoading(false);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load datasets');
                setLoading(false);
            }
        };

        fetchDatasets();
    }, []);

    if (loading) {
        return (
            <div className="step-content">
                <h2>Select Dataset to Import</h2>
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading datasets...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="step-content">
                <h2>Select Dataset to Import</h2>
                <div className="error-state">
                    <span className="error-icon">⚠️</span>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    if (datasets.length === 0) {
        return (
            <div className="step-content">
                <h2>Select Dataset to Import</h2>
                <div className="empty-state">
                    <span className="empty-icon">📂</span>
                    <h3>No Datasets Available</h3>
                    <p>Upload a dataset first to use the import feature.</p>
                    <button
                        className="btn-primary"
                        onClick={() => window.location.href = '/datasets'}
                    >
                        Go to Data Sources
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="step-content">
            <h2>Select Dataset to Import</h2>
            <p>Choose a loaded dataset from your data sources.</p>

            <div className="dataset-list">
                {datasets.map((dataset) => (
                    <div key={dataset.id} className="dataset-card">
                        <div className="dataset-icon">📊</div>
                        <div className="dataset-info">
                            <h3>{dataset.name}</h3>
                            <p>
                                {dataset.row_count?.toLocaleString() || 0} rows • {dataset.column_count || 0} columns • {dataset.file_type?.toUpperCase() || 'N/A'}
                            </p>
                        </div>
                        <button
                            className="btn-select"
                            onClick={() => onNext(dataset)}
                        >
                            Select
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Step 2: Select Target
const SelectTargetStep: React.FC<{
    onNext: () => void;
    onBack: () => void;
    selectedDataset: Dataset | null;
}> = ({ onNext, onBack, selectedDataset }) => {
    return (
        <div className="step-content">
            <h2>Select Target Database & Table</h2>
            <p>Choose the destination for your data.</p>

            {selectedDataset && (
                <div className="selected-dataset-info">
                    <strong>Selected Dataset:</strong> {selectedDataset.name}
                </div>
            )}

            <div className="form-group">
                <label>Database Connection</label>
                <select className="form-control">
                    <option>Select connection...</option>
                    <option>Production DB</option>
                </select>
            </div>

            <div className="form-group">
                <label>Schema</label>
                <select className="form-control">
                    <option>public</option>
                </select>
            </div>

            <div className="form-group">
                <label>Table</label>
                <select className="form-control">
                    <option>Select table...</option>
                </select>
            </div>

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack}>
                    ← Back
                </button>
                <button className="btn-primary" onClick={onNext}>
                    Next →
                </button>
            </div>
        </div>
    );
};

// Step 3: Map Columns
const MapColumnsStep: React.FC<{ onNext: () => void; onBack: () => void }> = ({
    onNext,
    onBack,
}) => {
    return (
        <div className="step-content">
            <h2>Map Columns</h2>
            <p>Map source columns to target table columns.</p>

            <button className="btn-auto-map">✨ Auto-Map Columns</button>

            <div className="mapping-table">
                <table>
                    <thead>
                        <tr>
                            <th>Source Column</th>
                            <th>Type</th>
                            <th>→</th>
                            <th>Target Column</th>
                            <th>Type</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>id</td>
                            <td><span className="type-badge">integer</span></td>
                            <td>→</td>
                            <td>
                                <select className="form-control-sm">
                                    <option>id</option>
                                </select>
                            </td>
                            <td><span className="type-badge">integer</span></td>
                            <td><span className="status-ok">✓ Compatible</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack}>
                    ← Back
                </button>
                <button className="btn-primary" onClick={onNext}>
                    Next →
                </button>
            </div>
        </div>
    );
};

// Step 4: Preview & Validate
const PreviewValidateStep: React.FC<{ onNext: () => void; onBack: () => void }> = ({
    onNext,
    onBack,
}) => {
    return (
        <div className="step-content">
            <h2>Preview & Validate</h2>
            <p>Review data preview and validation results.</p>

            <div className="validation-summary">
                <div className="validation-item success">
                    <span className="icon">✓</span>
                    <span>All column mappings valid</span>
                </div>
                <div className="validation-item success">
                    <span className="icon">✓</span>
                    <span>No type mismatches detected</span>
                </div>
                <div className="validation-item warning">
                    <span className="icon">⚠</span>
                    <span>3 rows with null values in non-nullable columns</span>
                </div>
            </div>

            <div className="data-preview">
                <h3>Data Preview (First 10 rows)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>id</th>
                            <th>name</th>
                            <th>email</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td>John Doe</td>
                            <td>john@example.com</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack}>
                    ← Back
                </button>
                <button className="btn-primary" onClick={onNext}>
                    Next →
                </button>
            </div>
        </div>
    );
};

// Step 5: Configure Import
const ConfigureImportStep: React.FC<{ onNext: () => void; onBack: () => void }> = ({
    onNext,
    onBack,
}) => {
    return (
        <div className="step-content">
            <h2>Configure Import Options</h2>
            <p>Set import behavior and options.</p>

            <div className="form-group">
                <label>Import Mode</label>
                <select className="form-control">
                    <option>INSERT - Add new rows only</option>
                    <option>UPSERT - Insert or update existing rows</option>
                    <option>TRUNCATE & INSERT - Clear table and insert</option>
                </select>
            </div>

            <div className="form-group">
                <label>Batch Size</label>
                <input type="number" className="form-control" defaultValue={1000} />
            </div>

            <div className="form-group">
                <label className="checkbox-label">
                    <input type="checkbox" />
                    Stop on first error
                </label>
            </div>

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack}>
                    ← Back
                </button>
                <button className="btn-primary" onClick={onNext}>
                    Next →
                </button>
            </div>
        </div>
    );
};

// Step 6: Execute
const ExecuteStep: React.FC<{ onBack: () => void }> = ({ onBack }) => {
    const [executing, setExecuting] = useState(false);

    return (
        <div className="step-content">
            <h2>Execute Import</h2>
            <p>Review and execute the import operation.</p>

            <div className="import-summary">
                <h3>Import Summary</h3>
                <div className="summary-item">
                    <strong>Dataset:</strong> Sample Dataset
                </div>
                <div className="summary-item">
                    <strong>Target:</strong> Production DB &gt; public.users
                </div>
                <div className="summary-item">
                    <strong>Rows:</strong> 1,234
                </div>
                <div className="summary-item">
                    <strong>Mode:</strong> INSERT
                </div>
            </div>

            {executing && (
                <div className="import-progress">
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: '45%' }} />
                    </div>
                    <p>Importing... 450 / 1,234 rows (45%)</p>
                </div>
            )}

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack} disabled={executing}>
                    ← Back
                </button>
                <button
                    className="btn-danger"
                    onClick={() => setExecuting(true)}
                    disabled={executing}
                >
                    {executing ? '⏳ Importing...' : '▶️ Execute Import'}
                </button>
            </div>
        </div>
    );
};
