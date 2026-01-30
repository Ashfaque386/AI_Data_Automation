import React from 'react'
import { SQLEditor } from '../components/SQLEditor'
import './SQLPage.css'

export const SQLPage: React.FC = () => {
    return (
        <div className="sql-page">
            <SQLEditor />
        </div>
    )
}
