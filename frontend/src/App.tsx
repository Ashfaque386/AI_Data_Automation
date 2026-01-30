import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { Settings } from './pages/Settings'
import { SQLPage } from './pages/SQLPage'
import { DatasetsPage } from './pages/DatasetsPage'
import { FilesPage } from './pages/FilesPage'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { useAuthStore } from './store'
import { authApi } from './services/api'
import './App.css'

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { isAuthenticated } = useAuthStore()
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }
    return <>{children}</>
}

const App: React.FC = () => {
    const { isAuthenticated, setUser } = useAuthStore()
    // We still sync route to activePage for Sidebar highlighting if needed, 
    // or we can refactor Sidebar to use useLocation. 
    // For now, Sidebar uses store, so we might need to sync or refactor Sidebar.
    // Let's refactor Sidebar later to rely on location or Link active state.

    // Check auth status
    useEffect(() => {
        if (isAuthenticated) {
            authApi.getCurrentUser()
                .then((response) => setUser(response.data))
                .catch(() => useAuthStore.getState().logout())
        }
    }, [isAuthenticated, setUser])

    return (
        <div className="app-layout">
            {isAuthenticated && <Sidebar />}
            <div className="app-main">
                {isAuthenticated && <TopBar />}
                <div className="app-workspace">
                    <Routes>
                        <Route path="/login" element={
                            isAuthenticated ? <Navigate to="/" replace /> : <Login />
                        } />

                        <Route path="/" element={
                            <ProtectedRoute>
                                <div className="workspace-content">
                                    <Home />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/settings" element={
                            <ProtectedRoute>
                                <div className="workspace-content">
                                    <Settings />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/sql" element={
                            <ProtectedRoute>
                                <div className="workspace-content" style={{ overflow: 'hidden' }}>
                                    <SQLPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/datasets" element={
                            <ProtectedRoute>
                                <div className="workspace-content" style={{ overflow: 'hidden' }}>
                                    <DatasetsPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/upload" element={
                            <ProtectedRoute>
                                <div className="workspace-content" style={{ overflow: 'hidden' }}>
                                    <DatasetsPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/files" element={
                            <ProtectedRoute>
                                <div className="workspace-content" style={{ overflow: 'hidden' }}>
                                    <FilesPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/jobs" element={<ProtectedRoute><div className="page-placeholder">Jobs (Coming Soon)</div></ProtectedRoute>} />
                        <Route path="/audit" element={<ProtectedRoute><div className="page-placeholder">Audit Logs (Coming Soon)</div></ProtectedRoute>} />

                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </div>
            </div>
        </div>
    )
}

export default App
