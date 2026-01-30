import React, { useState } from 'react'
import { useAuthStore } from '../store'
import './Login.css'

export const Login: React.FC = () => {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const { login, isLoading } = useAuthStore()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        try {
            await login(email, password)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed')
        }
    }

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <h1>Enterprise Data Operations</h1>
                    <p>Sign in to access the platform</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="form-group">
                        <label>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoFocus
                        />
                    </div>

                    <div className="form-group">
                        <label>Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button type="submit" className="btn btn-primary btn-block" disabled={isLoading}>
                        {isLoading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <div className="login-footer">
                    <p>Default credentials: admin@example.com / admin123</p>
                </div>
            </div>
        </div>
    )
}
