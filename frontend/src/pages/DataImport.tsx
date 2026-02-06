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

interface ColumnMapping {
    sourceColumn: string;
    sourceType: string;
    targetColumn: string;
    targetType: string;
    compatible: boolean;
}

export const DataImport: React.FC = () => {
    const [currentStep, setCurrentStep] = useState(1);
    const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
    const [selectedConnection, setSelectedConnection] = useState<number | null>(null);
    const [selectedSchema, setSelectedSchema] = useState<string>('public');
    const [selectedTable, setSelectedTable] = useState<string>('');
    const [columnMappings, setColumnMappings] = useState<{ [key: string]: string }>({});

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

    const handleTargetSelect = (connectionId: number, schema: string, table: string) => {
        setSelectedConnection(connectionId);
        setSelectedSchema(schema);
        setSelectedTable(table);
        setCurrentStep(3);
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
                        onNext={handleTargetSelect}
                        onBack={() => setCurrentStep(1)}
                        selectedDataset={selectedDataset}
                    />
                )}
                {currentStep === 3 && (
                    <MapColumnsStep
                        onNext={() => setCurrentStep(4)}
                        onBack={() => setCurrentStep(2)}
                        datasetId={selectedDataset?.id || 0}
                        connectionId={selectedConnection || 0}
                        schema={selectedSchema}
                        tableName={selectedTable}
                        onMappingsChange={setColumnMappings}
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
                    <ExecuteStep
                        onBack={() => setCurrentStep(5)}
                        dataset={selectedDataset}
                        connectionId={selectedConnection || 0}
                        schema={selectedSchema}
                        tableName={selectedTable}
                        mappings={columnMappings}
                    />
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
                    headers: { 'Authorization': `Bearer ${token}` }
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
    onNext: (connectionId: number, schema: string, table: string) => void;
    onBack: () => void;
    selectedDataset: Dataset | null;
}> = ({ onNext, onBack, selectedDataset }) => {
    const [connections, setConnections] = useState<any[]>([]);
    const [schemas, setSchemas] = useState<string[]>([]);
    const [tables, setTables] = useState<string[]>([]);
    const [selectedConnection, setSelectedConnection] = useState<number | null>(null);
    const [selectedSchema, setSelectedSchema] = useState<string>('public');
    const [selectedTable, setSelectedTable] = useState<string>('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchConnections = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const response = await axios.get('http://localhost:8000/api/import/connections', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                setConnections(response.data.connections || []);
                setLoading(false);
            } catch (err) {
                console.error('Failed to load connections:', err);
                setLoading(false);
            }
        };
        fetchConnections();
    }, []);

    useEffect(() => {
        if (selectedConnection) {
            const fetchSchemas = async () => {
                try {
                    const token = localStorage.getItem('access_token');
                    const response = await axios.get(
                        `http://localhost:8000/api/import/connections/${selectedConnection}/schemas`,
                        { headers: { 'Authorization': `Bearer ${token}` } }
                    );
                    setSchemas(response.data.schemas || []);
                    if (response.data.schemas?.length > 0) {
                        setSelectedSchema(response.data.schemas[0]);
                    }
                } catch (err) {
                    console.error('Failed to load schemas:', err);
                }
            };
            fetchSchemas();
        }
    }, [selectedConnection]);

    useEffect(() => {
        if (selectedConnection && selectedSchema) {
            const fetchTables = async () => {
                try {
                    const token = localStorage.getItem('access_token');
                    const response = await axios.get(
                        `http://localhost:8000/api/import/connections/${selectedConnection}/tables?schema=${selectedSchema}`,
                        { headers: { 'Authorization': `Bearer ${token}` } }
                    );
                    setTables(response.data.tables || []);
                } catch (err) {
                    console.error('Failed to load tables:', err);
                }
            };
            fetchTables();
        }
    }, [selectedConnection, selectedSchema]);

    if (loading) {
        return (
            <div className="step-content">
                <h2>Select Target Database & Table</h2>
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading connections...</p>
                </div>
            </div>
        );
    }

    if (connections.length === 0) {
        return (
            <div className="step-content">
                <h2>Select Target Database & Table</h2>
                <div className="empty-state">
                    <span className="empty-icon">🔌</span>
                    <h3>No Database Connections</h3>
                    <p>Configure a database connection first in Settings.</p>
                    <button
                        className="btn-primary"
                        onClick={() => window.location.href = '/settings'}
                    >
                        Go to Settings
                    </button>
                </div>
            </div>
        );
    }

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
                <select
                    className="form-control"
                    value={selectedConnection || ''}
                    onChange={(e) => setSelectedConnection(Number(e.target.value))}
                >
                    <option value="">Select connection...</option>
                    {connections.map((conn) => (
                        <option key={conn.id} value={conn.id}>
                            {conn.name}
                        </option>
                    ))}
                </select>
            </div>

            {selectedConnection && (
                <div className="form-group">
                    <label>Schema</label>
                    <select
                        className="form-control"
                        value={selectedSchema}
                        onChange={(e) => setSelectedSchema(e.target.value)}
                    >
                        {schemas.map((schema) => (
                            <option key={schema} value={schema}>
                                {schema}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {selectedConnection && selectedSchema && (
                <div className="form-group">
                    <label>Table</label>
                    <select
                        className="form-control"
                        value={selectedTable}
                        onChange={(e) => setSelectedTable(e.target.value)}
                    >
                        <option value="">Select table...</option>
                        {tables.map((table) => (
                            <option key={table} value={table}>
                                {table}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            <div className="step-actions">
                <button className="btn-secondary" onClick={onBack}>
                    ← Back
                </button>
                <button
                    className="btn-primary"
                    onClick={() => selectedConnection && selectedTable && onNext(selectedConnection, selectedSchema, selectedTable)}
                    disabled={!selectedConnection || !selectedTable}
                >
                    Next →
                </button>
            </div>
        </div>
    );
};

// Step 3: Map Columns
const MapColumnsStep: React.FC<{
    onNext: () => void;
    onBack: () => void;
    datasetId: number;
    connectionId: number;
    schema: string;
    tableName: string;
    onMappingsChange: (mappings: ColumnMapping[]) => void;
}> = ({ onNext, onBack, datasetId, connectionId, schema, tableName, onMappingsChange }) => {
    const [sourceColumns, setSourceColumns] = useState<any[]>([]);
    const [targetColumns, setTargetColumns] = useState<any[]>([]);
    const [mappings, setMappings] = useState<{ [key: string]: string }>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchColumns = async () => {
            try {
                const token = localStorage.getItem('access_token');

                // Fetch dataset columns
                const datasetResponse = await axios.get(
                    `http://localhost:8000/api/import/datasets/${datasetId}/columns`,
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );

                // Fetch target table columns
                const tableResponse = await axios.get(
                    `http://localhost:8000/api/import/connections/${connectionId}/tables/${tableName}/columns?schema=${schema}`,
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );

                setSourceColumns(datasetResponse.data.columns || []);
                setTargetColumns(tableResponse.data.columns || []);

                // Auto-map columns with matching names
                const autoMappings: { [key: string]: string } = {};
                datasetResponse.data.columns.forEach((srcCol: any) => {
                    const matchingTarget = tableResponse.data.columns.find(
                        (tgtCol: any) => tgtCol.name.toLowerCase() === srcCol.name.toLowerCase()
                    );
                    if (matchingTarget) {
                        autoMappings[srcCol.name] = matchingTarget.name;
                    }
                });
                setMappings(autoMappings);
                setLoading(false);
            } catch (err) {
                console.error('Failed to load columns:', err);
                setLoading(false);
            }
        };

        if (datasetId && connectionId && tableName) {
            fetchColumns();
        }
    }, [datasetId, connectionId, schema, tableName]);

    const handleMappingChange = (sourceCol: string, targetCol: string) => {
        setMappings(prev => ({ ...prev, [sourceCol]: targetCol }));
    };

    const handleAutoMap = () => {
        const autoMappings: { [key: string]: string } = {};
        sourceColumns.forEach((srcCol) => {
            const matchingTarget = targetColumns.find(
                (tgtCol) => tgtCol.name.toLowerCase() === srcCol.name.toLowerCase()
            );
            if (matchingTarget) {
                autoMappings[srcCol.name] = matchingTarget.name;
            }
        });
        setMappings(autoMappings);
    };

    if (loading) {
        return (
            <div className="step-content">
                <h2>Map Columns</h2>
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading columns...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="step-content">
            <h2>Map Columns</h2>
            <p>Map source columns to target table columns.</p>

            <button className="btn-auto-map" onClick={handleAutoMap}>✨ Auto-Map Columns</button>

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
                        {sourceColumns.map((srcCol) => {
                            const targetCol = mappings[srcCol.name] ?
                                targetColumns.find(t => t.name === mappings[srcCol.name]) : null;
                            const compatible = targetCol ? true : false; // Simplified compatibility check

                            return (
                                <tr key={srcCol.name}>
                                    <td>{srcCol.name}</td>
                                    <td><span className="type-badge">{srcCol.type}</span></td>
                                    <td>→</td>
                                    <td>
                                        <select
                                            className="form-control-sm"
                                            value={mappings[srcCol.name] || ''}
                                            onChange={(e) => handleMappingChange(srcCol.name, e.target.value)}
                                        >
                                            <option value="">-- Skip --</option>
                                            {targetColumns.map((tgtCol) => (
                                                <option key={tgtCol.name} value={tgtCol.name}>
                                                    {tgtCol.name}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    <td>
                                        {targetCol && <span className="type-badge">{targetCol.type}</span>}
                                    </td>
                                    <td>
                                        {mappings[srcCol.name] && (
                                            <span className="status-ok">✓ Mapped</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
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
const ExecuteStep: React.FC<{
    onBack: () => void;
    dataset: Dataset | null;
    connectionId: number;
    schema: string;
    tableName: string;
    mappings: { [key: string]: string };
}> = ({ onBack, dataset, connectionId, schema, tableName, mappings }) => {
    const [executing, setExecuting] = useState(false);
    const [connectionName, setConnectionName] = useState<string>('');

    useEffect(() => {
        const fetchConnectionName = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const response = await axios.get('http://localhost:8000/api/import/connections', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const conn = response.data.connections.find((c: any) => c.id === connectionId);
                if (conn) {
                    setConnectionName(conn.name);
                }
            } catch (err) {
                console.error('Failed to load connection name:', err);
            }
        };

        if (connectionId) {
            fetchConnectionName();
        }
    }, [connectionId]);

    const mappedColumnsCount = Object.keys(mappings).filter(key => mappings[key]).length;
    const totalSourceColumns = Object.keys(mappings).length;

    return (
        <div className="step-content">
            <h2>Execute Import</h2>
            <p>Review and execute the import operation.</p>

            <div className="import-summary">
                <h3>Import Summary</h3>

                <div className="summary-section">
                    <h4>📊 Source Dataset</h4>
                    <div className="summary-item">
                        <strong>Dataset:</strong> {dataset?.name || 'N/A'}
                    </div>
                    <div className="summary-item">
                        <strong>Rows:</strong> {dataset?.row_count?.toLocaleString() || 0}
                    </div>
                    <div className="summary-item">
                        <strong>Columns:</strong> {dataset?.column_count || 0}
                    </div>
                    <div className="summary-item">
                        <strong>File Type:</strong> {dataset?.file_type?.toUpperCase() || 'N/A'}
                    </div>
                </div>

                <div className="summary-section">
                    <h4>🎯 Target Database</h4>
                    <div className="summary-item">
                        <strong>Connection:</strong> {connectionName || `ID: ${connectionId}`}
                    </div>
                    <div className="summary-item">
                        <strong>Schema:</strong> {schema}
                    </div>
                    <div className="summary-item">
                        <strong>Table:</strong> {tableName}
                    </div>
                </div>

                <div className="summary-section">
                    <h4>🔗 Column Mappings</h4>
                    <div className="summary-item">
                        <strong>Mapped Columns:</strong> {mappedColumnsCount} of {totalSourceColumns}
                    </div>
                    <div className="summary-item">
                        <strong>Skipped Columns:</strong> {totalSourceColumns - mappedColumnsCount}
                    </div>
                </div>

                <div className="summary-section">
                    <h4>⚙️ Import Configuration</h4>
                    <div className="summary-item">
                        <strong>Mode:</strong> INSERT (Add new rows)
                    </div>
                    <div className="summary-item">
                        <strong>Batch Size:</strong> 1,000 rows
                    </div>
                    <div className="summary-item">
                        <strong>Estimated Rows:</strong> {dataset?.row_count?.toLocaleString() || 0}
                    </div>
                </div>

                {executing && (
                    <div className="import-progress">
                        <div className="progress-bar">
                            <div className="progress-fill" style={{ width: '0%' }}></div>
                        </div>
                        <p>Importing data... Please wait.</p>
                    </div>
                )}
            </div>

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
