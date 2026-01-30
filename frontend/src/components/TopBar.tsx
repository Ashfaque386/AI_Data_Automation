import React from 'react'
import { useAuthStore } from '../store'
import './TopBar.css'

export const TopBar: React.FC = () => {
    const { user, logout } = useAuthStore()

    return (
        <div className="topbar">
            <div className="topbar-actions">
                {/* Actions removed as per user request */}
            </div>

            <div className="topbar-right">
                <div className="topbar-status">
                    <span className="badge badge-success">● System Online</span>
                </div>

                <div className="topbar-user">
                    <span>{user?.email}</span>
                    <button className="btn btn-sm" onClick={logout}>
                        Logout
                    </button>
                </div>
            </div>
        </div>
    )
}
