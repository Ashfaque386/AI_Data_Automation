import React, { useState, useEffect } from 'react';
import { jobsApi } from '../../services/jobsApi';
import './DirectoryBrowser.css';

interface DirectoryBrowserProps {
    value: string;
    onChange: (path: string) => void;
}

interface DirectoryItem {
    name: string;
    path: string;
}

export const DirectoryBrowser: React.FC<DirectoryBrowserProps> = ({ value, onChange }) => {
    const [currentPath, setCurrentPath] = useState(value || '/');
    const [directories, setDirectories] = useState<DirectoryItem[]>([]);
    const [parentPath, setParentPath] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (isOpen) {
            loadDirectories(currentPath);
        }
    }, [isOpen, currentPath]);

    const loadDirectories = async (path: string) => {
        setLoading(true);
        setError(null);
        try {
            const data = await jobsApi.listDirectories(path);
            setDirectories(data.directories);
            setParentPath(data.parent_path);
            // Update internal state if the API returned a specialized path (e.g. normalized)
            if (data.current_path) {
                // optional: setCurrentPath(data.current_path);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to list directories');
        } finally {
            setLoading(false);
        }
    };

    const handleNavigate = (path: string) => {
        setCurrentPath(path);
    };

    const handleSelect = () => {
        onChange(currentPath);
        setIsOpen(false);
    };

    return (
        <div className="directory-browser">
            <div className="browser-input-group">
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder="/app/backups"
                    className="path-input"
                />
                <button
                    type="button"
                    className="btn-secondary browse-btn"
                    onClick={() => setIsOpen(!isOpen)}
                >
                    {isOpen ? 'Close' : 'Browse'}
                </button>
            </div>

            {isOpen && (
                <div className="browser-dropdown">
                    <div className="browser-header">
                        <span className="current-path">{currentPath}</span>
                        {parentPath && (
                            <button
                                type="button"
                                className="btn-icon up-btn"
                                onClick={() => handleNavigate(parentPath)}
                                title="Go Up"
                            >
                                ⬆️ Up
                            </button>
                        )}
                    </div>

                    <div className="browser-list">
                        {loading ? (
                            <div className="loading-indicator">Loading...</div>
                        ) : error ? (
                            <div className="error-message">{error}</div>
                        ) : directories.length === 0 ? (
                            <div className="empty-message">No directories found</div>
                        ) : (
                            <ul>
                                {directories.map((dir) => (
                                    <li key={dir.path} onClick={() => handleNavigate(dir.path)}>
                                        <span className="folder-icon">📁</span>
                                        <span className="folder-name">{dir.name}</span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <div className="browser-footer">
                        <button
                            type="button"
                            className="btn-primary select-btn"
                            onClick={handleSelect}
                        >
                            Select Current Path
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
