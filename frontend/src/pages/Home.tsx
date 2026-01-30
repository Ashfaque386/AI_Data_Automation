import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi, aiApi, setupApi } from '../services/api'
import { useAuthStore, useAppStore } from '../store'
import './Home.css'

export const Home: React.FC = () => {
    const { user } = useAuthStore()
    const { isDbConfigured, setIsDbConfigured } = useAppStore()
    const [dbStatus, setDbStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
    const [aiStatus, setAiStatus] = useState<'checking' | 'available' | 'unavailable'>('checking')

    useEffect(() => {
        const checkSystemStatus = async () => {
            // Check Database
            try {
                // Check status via API
                const response = await setupApi.getStatus()
                if (response.data.configured) {
                    setDbStatus('connected')
                    setIsDbConfigured(true)
                } else {
                    setDbStatus('disconnected')
                    setIsDbConfigured(false)
                }
            } catch (e) {
                setDbStatus('disconnected')
                setIsDbConfigured(false)
            }

            // Check AI
            try {
                await aiApi.getModels()
                setAiStatus('available')
            } catch (e) {
                setAiStatus('unavailable')
            }
        }

        checkSystemStatus()
    }, [setIsDbConfigured])

    return (
        <div className="home-container">
            <header className="home-header">
                <h1>Welcome, {user?.full_name || user?.username}!</h1>
                <p className="subtitle">Enterprise Data Operations Platform</p>
            </header>

            <div className="status-cards">
                <div className={`status-card ${dbStatus}`}>
                    <div className="status-icon">🗄️</div>
                    <div className="status-info">
                        <h3>Database Connection</h3>
                        <p>{dbStatus === 'connected' ? 'Active' : 'Not Configured'}</p>
                    </div>
                    {dbStatus === 'disconnected' && (
                        <Link to="/settings" className="btn btn-sm btn-outline">Configure</Link>
                    )}
                </div>

                <div className={`status-card ${aiStatus}`}>
                    <div className="status-icon">🤖</div>
                    <div className="status-info">
                        <h3>AI Service</h3>
                        <p>{aiStatus === 'available' ? 'Online' : 'Offline'}</p>
                    </div>
                    {aiStatus === 'unavailable' && (
                        <Link to="/settings" className="btn btn-sm btn-outline">Setup</Link>
                    )}
                </div>
            </div>

            <div className="quick-actions">
                <h2>Quick Actions</h2>
                <div className="action-grid">
                    <Link to="/upload" className="action-card">
                        <span className="icon">📤</span>
                        <span>Upload Data</span>
                    </Link>
                    <Link to="/sql" className="action-card">
                        <span className="icon">⚡</span>
                        <span>Run SQL</span>
                    </Link>
                    <Link to="/settings" className="action-card">
                        <span className="icon">⚙️</span>
                        <span>Settings</span>
                    </Link>
                </div>
            </div>

            <div className="info-section">
                <h3>Getting Started</h3>
                <ul>
                    <li><strong>Connect Data:</strong> Go to Settings to connect your PostgreSQL database.</li>
                    <li><strong>Upload Files:</strong> Upload Excel or CSV files to analyze them with DuckDB.</li>
                    <li><strong>AI Analysis:</strong> Use the AI Assistant in SQL Workspace to generate queries.</li>
                </ul>
            </div>
        </div>
    )
}
