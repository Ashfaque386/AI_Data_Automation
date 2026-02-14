/**
 * Connection Modal Component
 * Add/Edit database connection
 */
import React, { useState, useEffect } from 'react';
import connectionsApi, { Connection, ConnectionCreate } from '../../services/connectionsApi';
import './ConnectionModal.css';

interface ConnectionModalProps {
    connection: Connection | null;
    onClose: () => void;
    onSave: () => void;
}

type ConnectionMethod = 'form' | 'string';

const ConnectionModal: React.FC<ConnectionModalProps> = ({ connection, onClose, onSave }) => {
    const [formData, setFormData] = useState<ConnectionCreate>({
        name: '',
        description: '',
        db_type: 'postgresql',
        connection_group: 'development',
        connection_mode: 'read_write',
        host: 'localhost',
        port: 5432,
        database: '',
        username: '',
        password: '',
        connection_string: '',
        schema: 'public',
        ssl_enabled: false,
        pool_size: 5,
        max_connections: 10,
        timeout_seconds: 30,
        is_read_only: false,
        is_default: false,
    });

    const [connectionMethod, setConnectionMethod] = useState<ConnectionMethod>('form');
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [dbOptions, setDbOptions] = useState<string[]>([]);
    const [testSuccess, setTestSuccess] = useState(false);
    const [testMessage, setTestMessage] = useState('');
    const [showAdvanced, setShowAdvanced] = useState(false);

    useEffect(() => {
        if (connection) {
            setFormData({
                name: connection.name,
                description: connection.description || '',
                db_type: connection.db_type,
                connection_group: connection.connection_group || 'development',
                connection_mode: connection.connection_mode || 'read_write',
                host: connection.host || '',
                port: connection.port || 5432,
                database: connection.database,
                username: connection.username || '',
                password: '', // Don't populate for security
                connection_string: '', // Don't populate for security
                schema: connection.schema || 'public',
                ssl_enabled: connection.ssl_enabled,
                pool_size: connection.pool_size,
                max_connections: connection.max_connections,
                timeout_seconds: connection.timeout_seconds,
                is_read_only: connection.is_read_only,
                is_default: connection.is_default,
            });

            if (connection.has_connection_string) {
                setConnectionMethod('string');
            }

            // If editing, we assume connection works, but we don't list DBs automatically
            // to avoid slow loading. User can re-test to change DB.
            if (connection.database) {
                setDbOptions([connection.database]);
                setTestSuccess(true);
            }
        }
    }, [connection]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        const checked = (e.target as HTMLInputElement).checked;

        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value
        }));

        // Reset test success if critical connection params change
        if (['host', 'port', 'username', 'password', 'connection_string', 'db_type'].includes(name)) {
            setTestSuccess(false);
            setTestMessage('');
            // Only clear database if it's not the one we are editing
            if (!connection) {
                setFormData(prev => ({ ...prev, database: '' }));
            }
        }
    };

    const handleTestAndDiscover = async () => {
        // Minimal validation
        if (connectionMethod === 'form') {
            if (!formData.host || !formData.username) {
                setTestMessage('Please enter Host and Username to test connection.');
                setTestSuccess(false);
                return;
            }
        } else {
            if (!formData.connection_string) {
                setTestMessage('Please enter Connection String to test.');
                setTestSuccess(false);
                return;
            }
        }

        setTesting(true);
        setTestMessage('');
        setTestSuccess(false);
        setDbOptions([]);

        try {
            // We use discoverDatabases as a "Test & List" mechanism
            const dbs = await connectionsApi.discoverDatabases({
                db_type: formData.db_type,
                host: formData.host,
                port: formData.port,
                username: formData.username,
                password: formData.password,
                connection_string: formData.connection_string,
                schema: formData.schema
            });

            setDbOptions(dbs);
            setTestSuccess(true);
            setTestMessage('Connection Successful!');

            // If currently selected database is not in the list (or empty), select the first one
            if (dbs.length > 0) {
                if (!formData.database || !dbs.includes(formData.database)) {
                    setFormData(prev => ({ ...prev, database: dbs[0] }));
                }
            } else {
                setTestMessage('Connection successful, but no databases found.');
            }
        } catch (error: any) {
            console.error('Test failed:', error);
            setTestSuccess(false);
            setTestMessage(`Connection failed: ${error.response?.data?.detail || error.message}`);
        } finally {
            setTesting(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.database) {
            alert("Please select a database.");
            return;
        }

        setSaving(true);

        try {
            const payload = { ...formData };
            if (connectionMethod === 'form') {
                payload.connection_string = undefined;
            }

            if (connection) {
                await connectionsApi.updateConnection(connection.id, payload);
                alert('Connection updated successfully');
            } else {
                await connectionsApi.createConnection(payload);
                alert('Connection created successfully');
            }
            onSave();
        } catch (error: any) {
            console.error('Save failed:', error);
            alert(`Failed to save connection: ${error.response?.data?.detail || error.message}`);
        } finally {
            setSaving(false);
        }
    };

    const dbTypeOptions = [
        { value: 'postgresql', label: 'PostgreSQL', defaultPort: 5432 },
        { value: 'mongodb', label: 'MongoDB', defaultPort: 27017 },
    ];

    const handleDbTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const dbType = e.target.value;
        const option = dbTypeOptions.find(opt => opt.value === dbType);

        setFormData(prev => ({
            ...prev,
            db_type: dbType,
            port: option?.defaultPort || prev.port
        }));

        setTestSuccess(false);
        setTestMessage('');
        setDbOptions([]);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{connection ? 'Edit Connection' : 'Add Connection'}</h2>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <form onSubmit={handleSubmit} className="connection-form">
                    <div className="modal-body">
                        {/* Section: Basic Info */}
                        <div className="section-header">Basic Information</div>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Connection Name *</label>
                                <input
                                    type="text"
                                    name="name"
                                    value={formData.name}
                                    onChange={handleChange}
                                    required
                                    placeholder="Production DB"
                                />
                            </div>

                            <div className="form-group">
                                <label>Database Type *</label>
                                <select
                                    name="db_type"
                                    value={formData.db_type}
                                    onChange={handleDbTypeChange}
                                    required
                                >
                                    {dbTypeOptions.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Environment</label>
                                <select
                                    name="connection_group"
                                    value={formData.connection_group}
                                    onChange={handleChange}
                                >
                                    <option value="production">Production</option>
                                    <option value="staging">Staging</option>
                                    <option value="development">Development</option>
                                    <option value="analytics">Analytics</option>
                                    <option value="testing">Testing</option>
                                </select>
                            </div>
                        </div>


                        {/* Connection Configuration */}
                        <div className="section-header">Connection Details</div>

                        <div className="form-group">
                            <label>Connection Method</label>
                            <select
                                value={connectionMethod}
                                onChange={(e) => setConnectionMethod(e.target.value as ConnectionMethod)}
                                className="full-width-select"
                            >
                                <option value="form">Standard Parameters</option>
                                <option value="string">Connection String (URI)</option>
                            </select>
                        </div>

                        {connectionMethod === 'string' ? (
                            <div className="form-group">
                                <label>Connection String (URI) *</label>
                                <textarea
                                    name="connection_string"
                                    value={formData.connection_string}
                                    onChange={handleChange}
                                    rows={3}
                                    placeholder="mongodb+srv://user:password@cluster.mongodb.net/dbname?retryWrites=true"
                                    required={connectionMethod === 'string' && !connection}
                                    className="code-input"
                                />
                                {connection && connection.has_connection_string && !formData.connection_string && (
                                    <p className="help-text">Leave blank to keep existing connection string</p>
                                )}
                            </div>
                        ) : (
                            <>
                                {/* Form Mode Inputs */}
                                <div className="form-row">
                                    <div className="form-group" style={{ flex: 2 }}>
                                        <label>Host *</label>
                                        <input
                                            type="text"
                                            name="host"
                                            value={formData.host}
                                            onChange={handleChange}
                                            required={connectionMethod === 'form'}
                                            placeholder="localhost"
                                        />
                                    </div>

                                    <div className="form-group" style={{ flex: 1 }}>
                                        <label>Port *</label>
                                        <input
                                            type="number"
                                            name="port"
                                            value={formData.port}
                                            onChange={handleChange}
                                            required={connectionMethod === 'form'}
                                        />
                                    </div>
                                </div>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Username</label>
                                        <input
                                            type="text"
                                            name="username"
                                            value={formData.username}
                                            onChange={handleChange}
                                            placeholder="db_user"
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Password</label>
                                        <input
                                            type="password"
                                            name="password"
                                            value={formData.password}
                                            onChange={handleChange}
                                            placeholder={connection ? "Leave blank to keep current" : ""}
                                        />
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Test Connection Button */}
                        <div className="form-group" style={{ marginTop: '1rem' }}>
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={handleTestAndDiscover}
                                disabled={testing}
                            >
                                {testing ? 'Testing...' : 'Test Connection'}
                            </button>
                        </div>

                        {/* Test Result Message */}
                        {testMessage && (
                            <div className={`alert ${testSuccess ? 'alert-success' : 'alert-error'}`} style={{ marginBottom: '1rem' }}>
                                {testMessage}
                            </div>
                        )}

                        {/* Database Selection (Only after success) */}
                        {testSuccess && (
                            <div className="form-group slide-in">
                                <label>Select Database *</label>
                                <select
                                    name="database"
                                    value={formData.database}
                                    onChange={handleChange}
                                    required
                                >
                                    <option value="">-- Select Database --</option>
                                    {dbOptions.map(db => (
                                        <option key={db} value={db}>{db}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {/* Advanced Options Toggle */}
                        <div className="form-group" style={{ marginTop: '1.5rem', borderTop: '1px solid #333', paddingTop: '1rem' }}>
                            <button
                                type="button"
                                className="btn-link"
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                style={{ color: '#888', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                            >
                                <span>{showAdvanced ? '🔽' : '▶️'}</span>
                                {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Options'}
                            </button>
                        </div>

                        {showAdvanced && (
                            <div className="advanced-options fade-in" style={{ marginTop: '1rem' }}>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Schema</label>
                                        <input
                                            type="text"
                                            name="schema"
                                            value={formData.schema}
                                            onChange={handleChange}
                                            placeholder="public"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Access Mode</label>
                                        <select
                                            name="connection_mode"
                                            value={formData.connection_mode}
                                            onChange={handleChange}
                                        >
                                            <option value="read_write">Read/Write</option>
                                            <option value="read_only">Read Only</option>
                                            <option value="maintenance">Maintenance</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label>Description</label>
                                    <textarea
                                        name="description"
                                        value={formData.description}
                                        onChange={handleChange}
                                        rows={2}
                                    />
                                </div>
                                <div className="form-row" style={{ marginTop: '1rem' }}>
                                    <div className="form-group checkbox-group">
                                        <label>
                                            <input
                                                type="checkbox"
                                                name="ssl_enabled"
                                                checked={formData.ssl_enabled}
                                                onChange={handleChange}
                                            />
                                            Enable SSL
                                        </label>
                                    </div>
                                    <div className="form-group checkbox-group">
                                        <label>
                                            <input
                                                type="checkbox"
                                                name="pool_size" // Actually pooling isn't checkbox but user might want it simple
                                                checked={false} // dummy
                                                readOnly
                                                disabled
                                            />
                                            {/* Just showing SSL/Default as in previous version, pool size was hidden in main request */}
                                        </label>
                                    </div>
                                    <div className="form-group checkbox-group">
                                        <label>
                                            <input
                                                type="checkbox"
                                                name="is_default"
                                                checked={formData.is_default}
                                                onChange={handleChange}
                                            />
                                            Set as Default
                                        </label>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={saving || !testSuccess || !formData.database}>
                            {saving ? 'Saving...' : connection ? 'Update' : 'Save Configuration'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ConnectionModal;
