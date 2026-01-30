import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore, useAppStore } from '../store'
import './Sidebar.css'

export const Sidebar: React.FC = () => {
    const { sidebarCollapsed } = useAppStore()
    const { user } = useAuthStore()
    const location = useLocation()

    const menuItems = [
        { path: '/', label: 'Home', icon: '🏠' },
        { path: '/files', label: 'Uploaded Files', icon: '📁' },
        { path: '/datasets', label: 'Data Sources', icon: '📊' },
        { path: '/sql', label: 'SQL Workspace', icon: '⚡' },
        { path: '/jobs', label: 'Jobs & Schedulers', icon: '⏰' },
        { path: '/audit', label: 'Audit Logs', icon: '📋' },
        { path: '/settings', label: 'Settings', icon: '⚙️' },
    ]

    const isActive = (path: string) => {
        if (path === '/' && location.pathname !== '/') return false
        return location.pathname.startsWith(path)
    }

    if (sidebarCollapsed) {
        return (
            <div className="sidebar sidebar-collapsed">
                {menuItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`sidebar-item ${isActive(item.path) ? 'active' : ''}`}
                        title={item.label}
                    >
                        <span className="sidebar-icon">{item.icon}</span>
                    </Link>
                ))}
            </div>
        )
    }

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h2>Enterprise DataOps</h2>
            </div>

            <nav className="sidebar-nav">
                {menuItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`sidebar-item ${isActive(item.path) ? 'active' : ''}`}
                    >
                        <span className="sidebar-icon">{item.icon}</span>
                        <span className="sidebar-label">{item.label}</span>
                    </Link>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="sidebar-user">
                    <div className="user-avatar">{user?.username?.[0]?.toUpperCase() || '👤'}</div>
                    <div className="user-info">
                        <div className="user-name">{user?.full_name || user?.username || 'User'}</div>
                        <div className="user-role">Administrator</div>
                    </div>
                </div>
            </div>
        </div>
    )
}
