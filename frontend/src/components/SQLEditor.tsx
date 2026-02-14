import React, { useState } from 'react'
import { sqlApi, aiApi } from '../services/api'
import { AIModelSelector } from './AIModelSelector'
import ConnectionSelector from './connections/ConnectionSelector'
import { useAppStore } from '../store'
import './SQLEditor.css'

export const SQLEditor: React.FC = () => {
    const [query, setQuery] = useState('SELECT * FROM ')
    const [result, setResult] = useState<any>(null)
    const [isExecuting, setIsExecuting] = useState(false)
    const [isGenerating, setIsGenerating] = useState(false)
    const [nlPrompt, setNlPrompt] = useState('')
    const [showAiInput, setShowAiInput] = useState(false)
    const [selectedConnectionId, setSelectedConnectionId] = useState<number | undefined>()

    const { selectedModel } = useAppStore()

    const executeQuery = async () => {
        if (!query.trim()) return
        if (!selectedConnectionId) {
            alert('Please select a database connection first')
            return
        }

        setIsExecuting(true)
        try {
            // Use the new connection-based API
            const response = await sqlApi.execute(query, selectedConnectionId)
            setResult(response.data)
        } catch (error: any) {
            setResult({
                success: false,
                error_message: error.response?.data?.detail || 'Query execution failed',
            })
        } finally {
            setIsExecuting(false)
        }
    }

    const generateSQL = async () => {
        if (!nlPrompt.trim()) return

        setIsGenerating(true)
        try {
            const response = await aiApi.nlToSql(nlPrompt, [], selectedModel || undefined)
            if (response.data.success) {
                setQuery(response.data.sql)
                setShowAiInput(false)
            }
        } catch (error: any) {
            console.error('AI Generation failed:', error)
            alert('Failed to generate SQL: ' + (error.response?.data?.detail || error.message))
        } finally {
            setIsGenerating(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault()
            executeQuery()
        }
    }

    return (
        <div className="sql-editor-container">
            <div className="sql-editor-header">
                <h3>SQL Workspace</h3>
                <div className="sql-editor-controls">
                    <ConnectionSelector
                        selectedConnectionId={selectedConnectionId}
                        onConnectionChange={setSelectedConnectionId}
                        showHealthStatus={true}
                    />
                    <AIModelSelector />
                    <button
                        className={`btn btn-sm ${showAiInput ? 'btn-active' : ''}`}
                        onClick={() => setShowAiInput(!showAiInput)}
                        title="AI Assist"
                    >
                        ✨ AI Assist
                    </button>
                    <div className="divider-vertical"></div>
                    <div className="sql-editor-actions">
                        <button
                            className="btn btn-primary btn-sm"
                            onClick={executeQuery}
                            disabled={isExecuting}
                        >
                            {isExecuting ? '⏳ Running...' : '▶ Run (Ctrl+Enter)'}
                        </button>
                        <button className="btn btn-sm" onClick={() => setQuery('')}>
                            Clear
                        </button>
                    </div>
                </div>
            </div>

            {showAiInput && (
                <div className="ai-input-panel">
                    <input
                        type="text"
                        value={nlPrompt}
                        onChange={(e) => setNlPrompt(e.target.value)}
                        placeholder="Describe your query in plain English (e.g., 'Show me top 5 users by sales')..."
                        className="ai-input"
                        onKeyDown={(e) => e.key === 'Enter' && generateSQL()}
                    />
                    <button
                        className="btn btn-primary btn-sm"
                        onClick={generateSQL}
                        disabled={isGenerating || !nlPrompt.trim()}
                    >
                        {isGenerating ? '🤖 Generating...' : 'Generate SQL'}
                    </button>
                </div>
            )}

            <div className="sql-editor-input">
                <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter SQL query..."
                    spellCheck={false}
                />
            </div>

            {result && (
                <div className="sql-editor-results">
                    {result.success ? (
                        <>
                            <div className="result-header">
                                <span className="badge badge-success">✓ Success</span>
                                <span>{result.row_count} rows • {result.execution_time_ms}ms</span>
                            </div>

                            {result.data && result.data.length > 0 ? (
                                <div className="result-table-container">
                                    <table className="result-table">
                                        <thead>
                                            <tr>
                                                {result.columns.map((col: any) => (
                                                    <th key={col.name}>{col.name}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.data.slice(0, 100).map((row: any, idx: number) => (
                                                <tr key={idx}>
                                                    {result.columns.map((col: any) => (
                                                        <td key={col.name}>
                                                            {row[col.name] !== null ? String(row[col.name]) : 'NULL'}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                    {result.data.length > 100 && (
                                        <div className="result-truncated">
                                            Showing first 100 of {result.row_count} rows
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="result-empty">Query executed successfully (no results)</div>
                            )}
                        </>
                    ) : (
                        <div className="result-error">
                            <span className="badge badge-error">✗ Error</span>
                            <pre>{result.error_message}</pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
