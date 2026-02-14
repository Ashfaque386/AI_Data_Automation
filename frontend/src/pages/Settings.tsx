import React, { useState, useEffect } from 'react'
import DatabaseConnectionsPage from './DatabaseConnectionsPage'
import { setupApi, aiApi } from '../services/api'
import { useAppStore } from '../store'
import './Settings.css'

interface AIProvider {
    id: string
    name: string
    is_cloud: boolean
    requires_api_key: boolean
}

export const Settings: React.FC = () => {
    // Tab State
    const [activeTab, setActiveTab] = useState<'connections' | 'ai'>('connections')

    // DB State
    const [dbConfig, setDbConfig] = useState({
        host: 'host.docker.internal',
        port: 5432,
        user: 'postgres',
        password: '',
        database: ''
    })
    const [availableDbs, setAvailableDbs] = useState<string[]>([])
    const [isTesting, setIsTesting] = useState(false)
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
    const [isSaving, setIsSaving] = useState(false)
    const [currentDbStatus, setCurrentDbStatus] = useState<boolean>(false)
    const [showDbForm, setShowDbForm] = useState(false)

    // AI State
    const {
        availableModels,
        setAvailableModels,
        selectedModel,
        setSelectedModel,
        setIsDbConfigured
    } = useAppStore()

    const [providers, setProviders] = useState<AIProvider[]>([])
    const [aiMode, setAiMode] = useState<'local' | 'cloud'>('local') // Radio button state
    const [cloudProvider, setCloudProvider] = useState<string>('google') // Dropdown for cloud providers
    const [apiKey, setApiKey] = useState('')
    const [isAiTesting, setIsAiTesting] = useState(false)
    const [aiTestResult, setAiTestResult] = useState<{ success: boolean; message: string } | null>(null)
    const [isAiSaving, setIsAiSaving] = useState(false)

    useEffect(() => {
        checkStatus()
    }, [])

    const checkStatus = async () => {
        // Check DB Status
        try {
            const status = await setupApi.getStatus()
            setCurrentDbStatus(status.data.configured)
            setIsDbConfigured(status.data.configured)
            if (!status.data.configured) setShowDbForm(true)
        } catch (e) {
            console.error(e)
            setIsDbConfigured(false)
            setShowDbForm(true)
        }

        // Fetch AI Providers & Config
        try {
            const result = await aiApi.getProviders()
            setProviders(result.data)

            // Get Active Config
            const config = await aiApi.getActiveConfig()

            let activeModel = ''
            let activeProvider = 'ollama'

            if (config.data) {
                const isLocal = config.data.provider === 'ollama'
                setAiMode(isLocal ? 'local' : 'cloud')
                if (!isLocal) {
                    setCloudProvider(config.data.provider)
                    // If cloud, we might need to set API key from saved config if we want to show it (usually we don't return it)
                    // But we need it to fetch models if the endpoint requires it.
                    // The list_models endpoint should handle using the saved key if none provided.
                }
                activeModel = config.data.model_name || ''
                activeProvider = config.data.provider
            }

            // Load models first
            await loadModels(activeProvider, activeModel)

        } catch (e) {
            console.error("Failed to load AI config", e)
        }
    }

    const loadModels = async (providerId: string, preservedModel?: string) => {
        try {
            // Use current apiKey state or if checkStatus called us, it might rely on backend saved key
            const result = await aiApi.getModels(providerId, apiKey)
            let models = result.data.models

            // CRITICAL FIX: If we have a saved model that isn't in the fetched list,
            // we MUST add it to the list so it can be selected.
            if (preservedModel && !models.includes(preservedModel)) {
                models = [preservedModel, ...models]
            }

            setAvailableModels(models)

            if (preservedModel) {
                setSelectedModel(preservedModel)
            } else if (models.length > 0) {
                // Only reset to default if no model is currently selected
                // (or if we explicitly want to reset via empty preservedModel)
                if (!selectedModel) {
                    setSelectedModel(models[0])
                }
            }
        } catch (e) {
            setAvailableModels([])
            console.error("Failed to load models", e)
        }
    }

    const handleAiModeChange = (mode: 'local' | 'cloud') => {
        setAiMode(mode)
        setApiKey('')
        setAiTestResult(null)
        setSelectedModel('') // Clear model selection

        if (mode === 'local') {
            loadModels('ollama')
        } else {
            // Don't pass apiKey as preservedModel!
            loadModels(cloudProvider)
        }
    }

    const handleCloudProviderChange = (provider: string) => {
        setCloudProvider(provider)
        setApiKey('')
        setAiTestResult(null)
        setSelectedModel('') // Clear model selection
        loadModels(provider)
    }

    const handleAiTest = async () => {
        setIsAiTesting(true)
        setAiTestResult(null)

        const activeProvider = aiMode === 'local' ? 'ollama' : cloudProvider

        try {
            const result = await aiApi.testConnection({
                provider: activeProvider,
                model_name: selectedModel || 'default',
                api_key: apiKey,
                make_active: false
            })
            setAiTestResult(result.data)
            if (result.data.success) {
                // Don't pass key as preservedModel. Keep current selectedModel.
                loadModels(activeProvider, selectedModel || undefined)
            }
        } catch (e: any) {
            setAiTestResult({ success: false, message: e.response?.data?.message || 'Connection failed' })
        } finally {
            setIsAiTesting(false)
        }
    }

    const handleAiSave = async () => {
        setIsAiSaving(true)

        const activeProvider = aiMode === 'local' ? 'ollama' : cloudProvider

        try {
            await aiApi.saveConfig({
                provider: activeProvider,
                model_name: selectedModel,
                api_key: apiKey || undefined,
                make_active: true
            })
            setAiTestResult({ success: true, message: 'Configuration saved!' })
        } catch (e: any) {
            setAiTestResult({ success: false, message: e.response?.data?.message || 'Save failed' })
        } finally {
            setIsAiSaving(false)
        }
    }

    // DB handlers (unchanged)
    const handleTestConnection = async () => {
        setIsTesting(true)
        setTestResult(null)
        setAvailableDbs([])

        try {
            const response = await setupApi.testConnection({
                host: dbConfig.host,
                port: dbConfig.port,
                user: dbConfig.user,
                password: dbConfig.password
            })

            if (response.data.success) {
                setTestResult({ success: true, message: 'Connection Successful!' })
                setAvailableDbs(response.data.databases)
                if (!dbConfig.database && response.data.databases.length > 0) {
                    setDbConfig((prev: typeof dbConfig) => ({ ...prev, database: response.data.databases[0] }))
                }
            } else {
                setTestResult({ success: false, message: response.data.error || 'Connection failed' })
            }
        } catch (error: any) {
            setTestResult({
                success: false,
                message: error.response?.data?.detail || error.message || 'Connection failed'
            })
        } finally {
            setIsTesting(false)
        }
    }

    const handleSaveDb = async () => {
        if (!dbConfig.database) {
            setTestResult({ success: false, message: 'Please select a database' })
            return
        }

        setIsSaving(true)
        try {
            await setupApi.configure(dbConfig)
            setTestResult({ success: true, message: 'Database configured successfully!' })
            setIsDbConfigured(true)
            setCurrentDbStatus(true)
            setShowDbForm(false)
            setDbConfig((prev: typeof dbConfig) => ({ ...prev, password: '' }))
        } catch (error: any) {
            setTestResult({
                success: false,
                message: error.response?.data?.detail || 'Configuration failed'
            })
        } finally {
            setIsSaving(false)
        }
    }

    const cloudProviders = providers.filter(p => p.is_cloud)

    return (
        <div className="settings-container">
            <h1>System Settings</h1>

            <div className="settings-tabs">
                <button
                    className={`tab ${activeTab === 'connections' ? 'active' : ''}`}
                    onClick={() => setActiveTab('connections')}
                >
                    Database Connections
                </button>
                <button
                    className={`tab ${activeTab === 'ai' ? 'active' : ''}`}
                    onClick={() => setActiveTab('ai')}
                >
                    AI Configuration
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'connections' && (
                    <>
                        <DatabaseConnectionsPage />

                        <div className="settings-section" style={{ marginTop: '2rem' }}>
                            <div className="section-header">
                                <h2>🔌 Default Database Connection</h2>
                                <span className={`status-badge ${currentDbStatus ? 'connected' : 'disconnected'}`}>
                                    {currentDbStatus ? 'Active' : 'Not Configured'}
                                </span>
                            </div>

                            {!showDbForm && currentDbStatus ? (
                                <div className="connection-summary fade-in">
                                    <div className="alert alert-success">
                                        <strong>✓ Default database connected.</strong>
                                        <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', opacity: 0.9 }}>
                                            This connection is available in the SQL Workspace.
                                        </p>
                                    </div>
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => setShowDbForm(true)}
                                    >
                                        ⚙️ Reconfigure / Switch Database
                                    </button>
                                </div>
                            ) : (
                                <div className="connection-form fade-in">
                                    {currentDbStatus && (
                                        <div className="alert alert-warning" style={{ marginBottom: '1.5rem' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <span>Re-enter credentials to switch or update database connection.</span>
                                                <button
                                                    className="btn btn-sm"
                                                    onClick={() => setShowDbForm(false)}
                                                    style={{ background: 'transparent', border: '1px solid currentColor' }}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="form-grid">
                                        <div className="form-group">
                                            <label>Host</label>
                                            <input
                                                type="text"
                                                value={dbConfig.host}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDbConfig({ ...dbConfig, host: e.target.value })}
                                                placeholder="host.docker.internal"
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Port</label>
                                            <input
                                                type="number"
                                                value={dbConfig.port}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDbConfig({ ...dbConfig, port: parseInt(e.target.value) })}
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>User</label>
                                            <input
                                                type="text"
                                                value={dbConfig.user}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDbConfig({ ...dbConfig, user: e.target.value })}
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Password</label>
                                            <input
                                                type="password"
                                                value={dbConfig.password}
                                                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDbConfig({ ...dbConfig, password: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="action-row">
                                        <button
                                            className="btn btn-secondary"
                                            onClick={handleTestConnection}
                                            disabled={isTesting}
                                        >
                                            {isTesting ? 'Testing...' : 'Test Connection'}
                                        </button>
                                    </div>

                                    {testResult && (
                                        <div className={`alert ${testResult.success ? 'alert-success' : 'alert-error'}`}>
                                            {testResult.message}
                                        </div>
                                    )}

                                    {availableDbs.length > 0 && (
                                        <div className="db-selection slide-in">
                                            <div className="form-group">
                                                <label>Select Database</label>
                                                <select
                                                    value={dbConfig.database}
                                                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setDbConfig({ ...dbConfig, database: e.target.value })}
                                                >
                                                    {availableDbs.map((db: string) => (
                                                        <option key={db} value={db}>{db}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <button
                                                className="btn btn-primary"
                                                onClick={handleSaveDb}
                                                disabled={isSaving}
                                            >
                                                {isSaving ? 'Saving...' : 'Save Configuration'}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </>
                )}

                {activeTab === 'ai' && (
                    <div className="settings-section">
                        <div className="section-header">
                            <h2>🤖 AI Configuration</h2>
                            <span className={`status-badge ${aiMode === 'local' || availableModels.length > 0 ? 'connected' : 'disconnected'}`}>
                                {aiMode === 'local' ? 'Local' : 'Cloud'}
                            </span>
                        </div>

                        <div className="ai-mode-selection">
                            <label>AI Provider Type</label>
                            <div className="radio-group">
                                <label className="radio-option">
                                    <input
                                        type="radio"
                                        name="aiMode"
                                        value="local"
                                        checked={aiMode === 'local'}
                                        onChange={() => handleAiModeChange('local')}
                                    />
                                    <span>Local (Ollama)</span>
                                </label>
                                <label className="radio-option">
                                    <input
                                        type="radio"
                                        name="aiMode"
                                        value="cloud"
                                        checked={aiMode === 'cloud'}
                                        onChange={() => handleAiModeChange('cloud')}
                                    />
                                    <span>Cloud AI</span>
                                </label>
                            </div>
                        </div>

                        {aiMode === 'cloud' && (
                            <div className="form-group fade-in">
                                <label>Select Cloud Provider</label>
                                <select
                                    value={cloudProvider}
                                    onChange={(e) => handleCloudProviderChange(e.target.value)}
                                >
                                    {cloudProviders.map(p => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="ai-config-form fade-in" key={aiMode + cloudProvider}>
                            {aiMode === 'cloud' && (
                                <div className="form-group">
                                    <label>API Key</label>
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder={`Enter ${cloudProviders.find(p => p.id === cloudProvider)?.name} API Key`}
                                    />
                                    <small>Key is stored securely. Leave blank if unchanged.</small>
                                </div>
                            )}

                            <div className="form-group">
                                <label>Select Model</label>
                                {availableModels.length > 0 ? (
                                    <select
                                        value={selectedModel || ''}
                                        onChange={(e) => setSelectedModel(e.target.value)}
                                    >
                                        {availableModels.map((model: string) => (
                                            <option key={model} value={model}>
                                                {model}
                                            </option>
                                        ))}
                                    </select>
                                ) : (
                                    <div className="no-models">
                                        {aiMode === 'local' ?
                                            'No local models found. Ensure Ollama is running.' :
                                            'Enter API Key and Test Connection to load models.'}
                                    </div>
                                )}
                            </div>

                            <div className="action-row">
                                <button
                                    className="btn btn-secondary"
                                    onClick={handleAiTest}
                                    disabled={isAiTesting}
                                >
                                    {isAiTesting ? 'Testing...' : 'Test Connection'}
                                </button>

                                <button
                                    className="btn btn-primary"
                                    onClick={handleAiSave}
                                    disabled={isAiSaving}
                                >
                                    {isAiSaving ? 'Saving...' : 'Save Configuration'}
                                </button>
                            </div>

                            {aiTestResult && (
                                <div className={`alert ${aiTestResult.success ? 'alert-success' : 'alert-error'}`} style={{ marginTop: '1rem' }}>
                                    {aiTestResult.message}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
