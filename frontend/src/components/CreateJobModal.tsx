import React, { useState, useEffect } from 'react';
import { jobsApi, Job } from '../services/jobsApi';
import { ProcedureParameterInput } from './jobs/ProcedureParameterInput';
import { CronBuilder } from './jobs/CronBuilder';
import './CreateJobModal.css';

interface CreateJobModalProps {
    isOpen: boolean;
    onClose: () => void;
    onJobCreated: () => void;
    job?: Job | null; // Optional job for editing
}

interface ConnectionProfile {
    id: number;
    name: string;
    db_type: string;
}

interface Procedure {
    name: string;
    schema: string;
    type: string;
}

interface Parameter {
    name: string;
    data_type: string;
    parameter_mode: 'IN' | 'OUT' | 'INOUT';
    ordinal_position: number;
    parameter_default?: string;
}

export const CreateJobModal: React.FC<CreateJobModalProps> = ({ isOpen, onClose, onJobCreated, job }) => {
    const [jobType, setJobType] = useState('sql_script');
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [connectionId, setConnectionId] = useState<number | null>(null);
    const [sqlScript, setSqlScript] = useState('');
    const [cronExpression, setCronExpression] = useState('');
    const [isActive, setIsActive] = useState(true);
    const [connections, setConnections] = useState<ConnectionProfile[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Procedure-specific state
    const [procedures, setProcedures] = useState<Procedure[]>([]);
    const [selectedProcedure, setSelectedProcedure] = useState<string>('');
    const [procedureSchema, setProcedureSchema] = useState<string>('public');
    const [procedureParameters, setProcedureParameters] = useState<Parameter[]>([]);
    const [parameterValues, setParameterValues] = useState<Record<string, any>>({});
    const [loadingProcedures, setLoadingProcedures] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchConnections();
            if (job) {
                // Populate form for editing
                setName(job.name);
                setDescription(job.description || '');
                setJobType(job.job_type);
                // connection_id is generic in Job interface but we need it typed properly or cast
                if ((job as any).connection_id) setConnectionId((job as any).connection_id);
                setCronExpression(job.cron_expression || '');
                setIsActive(job.is_active);

                // Handle config population
                const config = (job as any).config || {};
                if (job.job_type === 'sql_script') {
                    setSqlScript(config.sql_script || '');
                } else if (job.job_type === 'stored_procedure') {
                    setSelectedProcedure(config.procedure_name || '');
                    setProcedureSchema(config.schema || 'public');

                    // Transform parameters list back to values map if needed
                    const paramsList = config.parameters || [];
                    const paramsMap: Record<string, any> = {};
                    if (Array.isArray(paramsList)) {
                        paramsList.forEach((p: any) => {
                            paramsMap[p.name] = p.value;
                        });
                    } else {
                        // Fallback for old dict format just in case
                        Object.assign(paramsMap, paramsList);
                    }
                    setParameterValues(paramsMap);
                } else if (job.job_type === 'database_backup') {
                    // No configurable path anymore
                }
            } else {
                // Reset form for create
                resetForm();
            }
        }
    }, [isOpen, job]);

    // Fetch procedures when connection + schema + jobType match, especially in edit mode
    useEffect(() => {
        if (isOpen && connectionId && jobType === 'stored_procedure') {
            // If editing, we might need to load procedures to populate the dropdown 
            // AND load parameters for the selected procedure
            fetchProcedures().then(() => {
                if (selectedProcedure) {
                    fetchProcedureParameters(selectedProcedure);
                }
            });
        }
    }, [isOpen, connectionId, jobType]); // Note: dependency on selectedProcedure removed to avoid loop, handled manually

    const resetForm = () => {
        setName('');
        setDescription('');
        setJobType('sql_script');
        setConnectionId(null);
        setSqlScript('');
        setCronExpression('');
        setIsActive(true);
        setSelectedProcedure('');
        setProcedureSchema('public');
        setProcedureParameters([]);
        setParameterValues({});
        setError(null);
    };

    const fetchConnections = async () => {
        setLoading(true);
        try {
            const data = await jobsApi.getConnections();
            setConnections(data);
            if (!job && data.length > 0 && !connectionId) {
                setConnectionId(data[0].id);
            }
        } catch (err) {
            console.error('Failed to fetch connections:', err);
            setError('Failed to load database connections');
        } finally {
            setLoading(false);
        }
    };

    const fetchProcedures = async () => {
        if (!connectionId) return;

        setLoadingProcedures(true);
        try {
            const response = await jobsApi.discoverProcedures(connectionId, procedureSchema);
            setProcedures(response.procedures || []);
        } catch (err) {
            console.error('Failed to fetch procedures:', err);
            setError('Failed to load procedures');
        } finally {
            setLoadingProcedures(false);
        }
    };

    const fetchProcedureParameters = async (procedureName: string) => {
        if (!connectionId) return;

        try {
            const response = await jobsApi.getProcedureParameters(
                procedureName,
                connectionId,
                procedureSchema
            );
            setProcedureParameters(response.parameters || []);
            // Don't reset values if we are editing and have them already
            if (!job) {
                setParameterValues({});
            }
        } catch (err) {
            console.error('Failed to fetch procedure parameters:', err);
            setError('Failed to load procedure parameters');
        }
    };

    const handleProcedureChange = (procedureName: string) => {
        setSelectedProcedure(procedureName);
        if (procedureName) {
            fetchProcedureParameters(procedureName);
            // Clear values only if changing procedure explicitly (user interaction)
            // If simply loading initial data, this check might need care. 
            // But handleProcedureChange is usually UI triggered.
            setParameterValues({});
        } else {
            setProcedureParameters([]);
            setParameterValues({});
        }
    };


    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            if (!connectionId) {
                throw new Error('Please select a database connection');
            }

            // Build config based on job type
            let config: any = {};

            if (jobType === 'sql_script') {
                if (!sqlScript.trim()) {
                    throw new Error('Please enter a SQL script');
                }
                config = { sql_script: sqlScript };
            } else if (jobType === 'stored_procedure') {
                if (!selectedProcedure) {
                    throw new Error('Please select a stored procedure');
                }
                // Transform parameters to list (sorted by ordinal_position)
                const formattedParameters = procedureParameters
                    .sort((a, b) => a.ordinal_position - b.ordinal_position)
                    .map(param => ({
                        name: param.name,
                        type: param.data_type,
                        value: parameterValues[param.name] ?? null
                    }));

                config = {
                    procedure_name: selectedProcedure,
                    schema: procedureSchema,
                    parameters: formattedParameters
                };
            } else if (jobType === 'database_backup') {
                config = {
                    backup_type: 'full',
                    compression_enabled: true
                };
            }

            const jobData = {
                name,
                description,
                job_type: jobType,
                connection_id: connectionId,
                is_active: isActive,
                cron_expression: cronExpression || undefined,
                config
            };

            if (job) {
                await jobsApi.updateJob(job.id, jobData);
            } else {
                await jobsApi.createJob(jobData);
            }

            onJobCreated(); // Helper name, maybe Rename to onSaved later
            handleClose();
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to save job');
        } finally {
            setLoading(false);
        }
    };


    const handleClose = () => {
        resetForm();
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{job ? 'Edit Job' : 'Create New Job'}</h2>
                    <button className="close-button" onClick={handleClose}>×</button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-section">
                        <h3>Basic Information</h3>

                        <div className="form-group">
                            <label>Job Name *</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Daily Data Cleanup"
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label>Description</label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Optional description of what this job does"
                                rows={3}
                            />
                        </div>

                        <div className="form-group">
                            <label>Job Type *</label>
                            <select
                                value={jobType}
                                onChange={(e) => setJobType(e.target.value)}
                                disabled={!!job} // Disable generic type change on edit to avoid config mismatch complexity
                            >
                                <option value="sql_script">SQL Script</option>
                                <option value="stored_procedure">Stored Procedure</option>
                                <option value="database_backup">Database Backup</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Database Connection *</label>
                            <select
                                value={connectionId || ''}
                                onChange={(e) => setConnectionId(Number(e.target.value))}
                                required
                            >
                                <option value="">Select a connection</option>
                                {connections.map(conn => (
                                    <option key={conn.id} value={conn.id}>
                                        {conn.name} ({conn.db_type})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* SQL Script Configuration */}
                    {jobType === 'sql_script' && (
                        <div className="form-section">
                            <h3>SQL Configuration</h3>

                            <div className="form-group">
                                <label>SQL Script *</label>
                                <textarea
                                    value={sqlScript}
                                    onChange={(e) => setSqlScript(e.target.value)}
                                    placeholder="Enter your SQL script here..."
                                    rows={8}
                                    className="sql-editor"
                                    required
                                />
                            </div>
                        </div>
                    )}

                    {/* Stored Procedure Configuration */}
                    {jobType === 'stored_procedure' && (
                        <div className="form-section">
                            <h3>Procedure Configuration</h3>

                            <div className="form-group">
                                <label>Schema</label>
                                <input
                                    type="text"
                                    value={procedureSchema}
                                    onChange={(e) => setProcedureSchema(e.target.value)}
                                    placeholder="public"
                                />
                            </div>

                            <div className="form-group">
                                <button
                                    type="button"
                                    onClick={fetchProcedures}
                                    className="btn-secondary"
                                    disabled={!connectionId || loadingProcedures}
                                >
                                    {loadingProcedures ? 'Loading...' : 'Discover Procedures'}
                                </button>
                            </div>

                            {procedures.length > 0 && (
                                <div className="form-group">
                                    <label>Select Procedure *</label>
                                    <select
                                        value={selectedProcedure}
                                        onChange={(e) => handleProcedureChange(e.target.value)}
                                        required
                                    >
                                        <option value="">Choose a procedure...</option>
                                        {procedures.map((proc) => (
                                            <option key={`${proc.schema}.${proc.name}`} value={proc.name}>
                                                {proc.schema}.{proc.name} ({proc.type})
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {selectedProcedure && procedureParameters.length > 0 && (
                                <ProcedureParameterInput
                                    parameters={procedureParameters}
                                    values={parameterValues}
                                    onChange={setParameterValues}
                                />
                            )}
                        </div>
                    )}

                    {/* Database Backup Configuration */}
                    {jobType === 'database_backup' && (
                        <div className="form-section">
                            <h3>Backup Configuration</h3>
                            <p className="info-message">
                                This will create a full database backup with compression enabled.
                                The backup file will be stored in the server's default backup directory.
                            </p>
                        </div>
                    )}


                    <div className="form-section">
                        <h3>Schedule (Optional)</h3>

                        <div className="form-group">
                            <label>Cron Expression</label>
                            <CronBuilder
                                value={cronExpression}
                                onChange={setCronExpression}
                            />
                        </div>

                        <div className="form-group checkbox-group">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={isActive}
                                    onChange={(e) => setIsActive(e.target.checked)}
                                />
                                <span>Active (job can be executed)</span>
                            </label>
                        </div>
                    </div>

                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    <div className="modal-footer">
                        <button type="button" onClick={handleClose} className="btn-secondary">
                            Cancel
                        </button>
                        <button type="submit" className="btn-primary" disabled={loading}>
                            {loading ? 'Saving...' : (job ? 'Update Job' : 'Create Job')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
