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
    const [sourceColumns, setSourceColumns] = useState<any[]>([]);
    const [targetColumns, setTargetColumns] = useState<any[]>([]);
    const [importMode, setImportMode] = useState<string>('insert');
    const [batchSize, setBatchSize] = useState<number>(1000);

    const steps = [
        { number: 1, title: 'Select Dataset', icon: '📊' },
        { number: 2, title: 'Select Target', icon: '🎯' },
        { number: 3, title: 'Map Columns', icon: '🔗' },
        { number: 4, title: 'Configure Import', icon: '⚙️' },
        { number: 5, title: 'Execute', icon: '▶️' },
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
                        onSourceColumnsLoaded={setSourceColumns}
                        onTargetColumnsLoaded={setTargetColumns}
                    />
                )}
                {currentStep === 4 && (
                    <ConfigureImportStep
                        onNext={() => setCurrentStep(5)}
                        onBack={() => setCurrentStep(3)}
                        importMode={importMode}
                        onImportModeChange={setImportMode}
                        batchSize={batchSize}
                        onBatchSizeChange={setBatchSize}
                    />
                )}
                {currentStep === 5 && (
                    <ExecuteStep
                        onBack={() => setCurrentStep(4)}
                        dataset={selectedDataset}
                        connectionId={selectedConnection || 0}
                        schema={selectedSchema}
                        tableName={selectedTable}
                        mappings={columnMappings}
                        sourceColumns={sourceColumns}
                        targetColumns={targetColumns}
                        importMode={importMode}
                        batchSize={batchSize}
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
    onMappingsChange: (mappings: { [key: string]: string }) => void;
    onSourceColumnsLoaded: (columns: any[]) => void;
    onTargetColumnsLoaded: (columns: any[]) => void;
}> = ({ onNext, onBack, datasetId, connectionId, schema, tableName, onMappingsChange, onSourceColumnsLoaded, onTargetColumnsLoaded }) => {
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

                const srcCols = datasetResponse.data.columns || [];
                setSourceColumns(srcCols);
                onSourceColumnsLoaded(srcCols);

                const tgtCols = tableResponse.data.columns || [];
                setTargetColumns(tgtCols);
                onTargetColumnsLoaded(tgtCols);

                // Auto-map columns with matching names
                const autoMappings: { [key: string]: string } = {};
                srcCols.forEach((srcCol: any) => {
                    const matchingTarget = tableResponse.data.columns.find(
                        (tgtCol: any) => tgtCol.name.toLowerCase() === srcCol.name.toLowerCase()
                    );
                    if (matchingTarget) {
                        autoMappings[srcCol.name] = matchingTarget.name;
                    }
                });
                setMappings(autoMappings);
                onMappingsChange(autoMappings); // Update parent state
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
        const newMappings = { ...mappings, [sourceCol]: targetCol };
        setMappings(newMappings);
        onMappingsChange(newMappings);
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
        onMappingsChange(autoMappings);
    };

    if (loading) {
        return (
            <div className="step-content">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading schema information...</p>
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
                            const targetColName = mappings[srcCol.name];
                            const targetCol = targetColumns.find(tc => tc.name === targetColName);
                            const isMapped = !!targetColName;

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
                                            {targetColumns.map(tc => (
                                                <option key={tc.name} value={tc.name}>
                                                    {tc.name} {tc.primary_key ? '(PK)' : ''}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    <td>
                                        {targetCol && <span className="type-badge">{targetCol.type}</span>}
                                    </td>
                                    <td>
                                        {isMapped ? (
                                            <span className="status-ok">✓ Mapped</span>
                                        ) : (
                                            <span className="status-skip">○ Skipped</span>
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
                    Next: Configure →
                </button>
            </div>
        </div>
    );
};

// Step 4: Configure Import
const ConfigureImportStep: React.FC<{
    onNext: () => void;
    onBack: () => void;
    importMode: string;
    onImportModeChange: (mode: string) => void;
    batchSize: number;
    onBatchSizeChange: (size: number) => void;
}> = ({
    onNext,
    onBack,
    importMode,
    onImportModeChange,
    batchSize,
    onBatchSizeChange,
}) => {
        return (
            <div className="step-content">
                <h2>Configure Import Options</h2>
                <p>Set import behavior and options.</p>

                <div className="form-group">
                    <label>Import Mode</label>
                    <select
                        className="form-control"
                        value={importMode}
                        onChange={(e) => onImportModeChange(e.target.value)}
                    >
                        <option value="insert">INSERT - Add new rows only</option>
                        <option value="upsert">UPSERT - Insert or update existing rows</option>
                        <option value="truncate_insert">TRUNCATE & INSERT - Clear table and insert</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>Batch Size</label>
                    <input
                        type="number"
                        className="form-control"
                        value={batchSize}
                        onChange={(e) => onBatchSizeChange(Number(e.target.value))}
                    />
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

// Step 5: Execute
const ExecuteStep: React.FC<{
    onBack: () => void;
    dataset: Dataset | null;
    connectionId: number;
    schema: string;
    tableName: string;
    mappings: { [key: string]: string };
    sourceColumns: any[];
    targetColumns: any[];
    importMode: string;
    batchSize: number;
}> = ({
    onBack,
    dataset,
    connectionId,
    schema,
    tableName,
    mappings,
    sourceColumns,
    targetColumns,
    importMode,
    batchSize,
}) => {
        const [executing, setExecuting] = useState(false);
        const [connectionName, setConnectionName] = useState<string>('');
        const [success, setSuccess] = useState(false);
        const [error, setError] = useState<string | null>(null);
        const [importStats, setImportStats] = useState<any>(null);

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

        const handleExecute = async () => {
            setExecuting(true);
            setError(null);

            try {
                const token = localStorage.getItem('access_token');
                // Convert mappings to API format using targetColumns for correct type info
                const apiMappings = Object.entries(mappings).map(([source, target]) => {
                    const sourceCol = sourceColumns.find(c => c.name === source);
                    const targetCol = targetColumns.find(c => c.name === target);
                    return {
                        source_column: source,
                        target_column: target,
                        source_type: sourceCol?.type || 'string',
                        target_type: targetCol?.type || 'string',
                        compatible: true
                    };
                }).filter(m => m.target_column);

                const payload = {
                    dataset_id: dataset?.id,
                    connection_id: connectionId,
                    target_table: tableName,
                    target_schema: schema,
                    import_mode: importMode,
                    mappings: apiMappings,
                    import_config: {
                        batch_size: batchSize,
                        stop_on_error: false
                    }
                };

                const response = await axios.post(
                    'http://localhost:8000/api/import/jobs',
                    payload,
                    { headers: { 'Authorization': `Bearer ${token}` } }
                );

                if (response.data.status === 'completed' && response.data.result.success) {
                    setSuccess(true);
                    setImportStats(response.data.result);
                } else {
                    setError(response.data.error || 'Import failed');
                }
            } catch (err: any) {
                console.error('Import execution failed:', err);
                const errorMsg = err.response?.data?.detail
                    ? (typeof err.response.data.detail === 'object' ? JSON.stringify(err.response.data.detail) : err.response.data.detail)
                    : 'Failed to execute import';
                setError(errorMsg);
            } finally {
                setExecuting(false);
            }
        };

        const mappedColumnsCount = Object.keys(mappings).filter(key => mappings[key]).length;
        const totalSourceColumns = Object.keys(mappings).length;

        if (success) {
            return (
                <div className="step-content">
                    <div className="success-message">
                        <h2>🎉 Import Successful!</h2>
                        <p>Your data has been successfully imported.</p>
                        <div className="stats-grid">
                            <div className="stat-card">
                                <span className="stat-value">{importStats?.inserted_rows || 0}</span>
                                <span className="stat-label">Inserted</span>
                            </div>
                            <div className="stat-card">
                                <span className="stat-value">{importStats?.updated_rows || 0}</span>
                                <span className="stat-label">Updated</span>
                            </div>
                            <div className="stat-card">
                                <span className="stat-value">{importStats?.error_rows || 0}</span>
                                <span className="stat-label">Errors</span>
                            </div>
                        </div>
                        <button className="btn-primary" onClick={() => window.location.reload()}>
                            Import Another Dataset
                        </button>
                    </div>
                </div>
            );
        }

        return (
            <div className="step-content">
                <h2>Execute Import</h2>
                <p>Review and execute the import operation.</p>

                {error && <div className="error-message">⚠️ {error}</div>}

                <div className="import-summary">
                    <h3>Import Summary</h3>
                    <div className="summary-section">
                        <h4>📊 Source Dataset</h4>
                        <div className="summary-item"><strong>Dataset:</strong> {dataset?.name}</div>
                        <div className="summary-item"><strong>Rows:</strong> {dataset?.row_count?.toLocaleString()}</div>
                    </div>
                    <div className="summary-section">
                        <h4>🎯 Target</h4>
                        <div className="summary-item"><strong>Connection:</strong> {connectionName}</div>
                        <div className="summary-item"><strong>Table:</strong> {schema}.{tableName}</div>
                    </div>
                    <div className="summary-section">
                        <h4>⚙️ Options</h4>
                        <div className="summary-item"><strong>Mode:</strong> {importMode.toUpperCase()}</div>
                        <div className="summary-item"><strong>Batch Size:</strong> {batchSize}</div>
                    </div>
                    <div className="summary-section">
                        <h4>🔗 Mappings</h4>
                        <div className="summary-item"><strong>Mapped:</strong> {mappedColumnsCount} column(s)</div>
                        <div className="summary-item"><strong>Skipped:</strong> {totalSourceColumns - mappedColumnsCount} column(s)</div>
                    </div>
                    {executing && (
                        <div className="import-progress">
                            <div className="progress-bar">
                                <div className="progress-fill" style={{ width: '100%', animation: 'progress 2s infinite' }}></div>
                            </div>
                            <p>Importing data...</p>
                        </div>
                    )}
                </div>

                <div className="step-actions">
                    <button className="btn-secondary" onClick={onBack} disabled={executing}>← Back</button>
                    <div className="action-buttons">
                        <button className="btn-secondary btn-danger-outline" onClick={onBack}>Discard</button>
                        <button className="btn-danger" onClick={handleExecute} disabled={executing}>
                            {executing ? '⏳ Importing...' : '▶️ Execute Import'}
                        </button>
                    </div>
                </div>
            </div>
        );
    };
