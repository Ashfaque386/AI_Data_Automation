import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { Settings } from './pages/Settings'
import { SQLPage } from './pages/SQLPage'
import { DatasetsPage } from './pages/DatasetsPage'
import { FilesPage } from './pages/FilesPage'
import { DataImport } from './pages/DataImport'
import { TableEntryPage } from './pages/TableEntryPage'
import { JobsPage } from './pages/JobsPage';
import DatabaseConnectionsPage from './pages/DatabaseConnectionsPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
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

// PersistentWrapper keeps the component mounted but hides it when not active
const PersistentWrapper: React.FC<{
    path: string;
    activePath: string;
    component: React.ReactNode
}> = ({ path, activePath, component }) => {
    // Check if the current active path starts with this path
    // We use startsWith to handle sub-routes if any (though currently flat)
    // Exact match is usually safer for tabs unless we have nested routing
    const isActive = activePath === path || activePath.startsWith(path + '/')

    return (
        <div
            style={{
                display: isActive ? 'flex' : 'none',
                flex: 1,
                flexDirection: 'column',
                height: '100%',
                width: '100%',
                overflow: 'hidden' // Container should not scroll, child workspace-content should
            }}
        >
            {component}
        </div>
    )
}

const App: React.FC = () => {
    const { isAuthenticated, setUser } = useAuthStore()
    const location = useLocation()

    // Check auth status
    useEffect(() => {
        if (isAuthenticated) {
            authApi.getCurrentUser()
                .then((response) => setUser(response.data))
                .catch(() => useAuthStore.getState().logout())
        }
    }, [isAuthenticated, setUser])

    // Memoize persistent page components to prevent re-renders and preserve state
    const [sqlPageState] = useState(() => (
        <SQLPage />
    ));

    const [datasetsPageState] = useState(() => (
        <DatasetsPage />
    ));

    const [filesPageState] = useState(() => (
        <FilesPage />
    ));

    const [dataImportPageState] = useState(() => (
        <DataImport />
    ));

    const [tableEntryPageState] = useState(() => (
        <TableEntryPage />
    ));

    const [jobsPageState] = useState(() => (
        <JobsPage />
    ));

    return (
        <div className="app-layout">
            {isAuthenticated && <Sidebar />}
            <div className="app-main">
                {isAuthenticated && <TopBar />}
                <div className="app-workspace">
                    {/*
                        ROUTER LOGIC:
                        We keep the Routes for non-persistent pages (Login, Home, Settings)
                        and for handling the "404" redirection logic.

                        For persistent pages, we define a Route that renders NULL.
                        This is critical so the Router knows "we are on a valid page"
                        and doesn't trigger the "*" catch-all redirect.
                    */}
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

                        {/*
                           PERSISTENT ROUTES PLACEHOLDERS
                           These render NOTHING to the DOM from the Router's perspective.
                           The actual visible content is handled by PersistentWrapper below.
                        */}
                        <Route path="/sql" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/datasets" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/upload" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/files" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/import" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/table-entry" element={<ProtectedRoute><></></ProtectedRoute>} />
                        <Route path="/jobs" element={<ProtectedRoute><></></ProtectedRoute>} />

                        <Route path="/connections" element={
                            <ProtectedRoute>
                                <div className="workspace-content">
                                    <DatabaseConnectionsPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="/audit" element={
                            <ProtectedRoute>
                                <div className="workspace-content">
                                    <AuditLogsPage />
                                </div>
                            </ProtectedRoute>
                        } />

                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>

                    {/*
                        PERSISTENT VIEWS
                        These are always mounted if authenticated, but hidden via CSS.
                        This strictly preserves state (inputs, scroll, results) when switching tabs.
                        Using flex: 1 and overflow: auto on the workspace-content ensures internal scrolling
                        SQLPage manages its own scroll via SQLEditor (overflow: hidden on container)
                        Others get overflow: auto for page scrolling
                    */}
                    {isAuthenticated && (
                        <>
                            <PersistentWrapper
                                path="/sql"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'hidden' }}>
                                        {sqlPageState}
                                    </div>
                                }
                            />

                            <PersistentWrapper
                                path="/datasets"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'auto' }}>
                                        {datasetsPageState}
                                    </div>
                                }
                            />

                            <PersistentWrapper
                                path="/files"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'auto' }}>
                                        {filesPageState}
                                    </div>
                                }
                            />

                            <PersistentWrapper
                                path="/import"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'auto' }}>
                                        {dataImportPageState}
                                    </div>
                                }
                            />

                            <PersistentWrapper
                                path="/table-entry"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'auto' }}>
                                        {tableEntryPageState}
                                    </div>
                                }
                            />

                            <PersistentWrapper
                                path="/jobs"
                                activePath={location.pathname}
                                component={
                                    <div className="workspace-content" style={{ overflow: 'auto' }}>
                                        {jobsPageState}
                                    </div>
                                }
                            />
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default App
