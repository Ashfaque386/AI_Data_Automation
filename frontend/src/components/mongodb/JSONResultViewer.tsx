/**
 * JSON Result Viewer Component
 * Displays MongoDB query results in a formatted JSON view
 */
import React, { useState } from 'react';
import './JSONResultViewer.css';

interface JSONResultViewerProps {
    data: any[];
}

export const JSONResultViewer: React.FC<JSONResultViewerProps> = ({ data }) => {
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const [viewMode, setViewMode] = useState<'pretty' | 'compact'>('pretty');

    const toggleExpand = (path: string) => {
        const newExpanded = new Set(expandedItems);
        if (newExpanded.has(path)) {
            newExpanded.delete(path);
        } else {
            newExpanded.add(path);
        }
        setExpandedItems(newExpanded);
    };

    const copyToClipboard = () => {
        const jsonString = JSON.stringify(data, null, 2);
        navigator.clipboard.writeText(jsonString);
        alert('Copied to clipboard!');
    };

    const downloadJSON = () => {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mongodb-results-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const renderValue = (value: any, path: string, depth: number = 0): JSX.Element => {
        if (value === null) {
            return <span className="json-null">null</span>;
        }

        if (typeof value === 'boolean') {
            return <span className="json-boolean">{value.toString()}</span>;
        }

        if (typeof value === 'number') {
            return <span className="json-number">{value}</span>;
        }

        if (typeof value === 'string') {
            return <span className="json-string">"{value}"</span>;
        }

        if (Array.isArray(value)) {
            const isExpanded = expandedItems.has(path);
            return (
                <span className="json-array">
                    <button className="expand-btn" onClick={() => toggleExpand(path)}>
                        {isExpanded ? '▼' : '▶'}
                    </button>
                    [
                    {isExpanded && (
                        <div className="json-nested">
                            {value.map((item, index) => (
                                <div key={index} className="json-item">
                                    {renderValue(item, `${path}[${index}]`, depth + 1)}
                                    {index < value.length - 1 && ','}
                                </div>
                            ))}
                        </div>
                    )}
                    {!isExpanded && value.length > 0 && <span className="json-ellipsis">...</span>}
                    ]
                </span>
            );
        }

        if (typeof value === 'object') {
            const isExpanded = expandedItems.has(path);
            const keys = Object.keys(value);
            return (
                <span className="json-object">
                    <button className="expand-btn" onClick={() => toggleExpand(path)}>
                        {isExpanded ? '▼' : '▶'}
                    </button>
                    {'{'}
                    {isExpanded && (
                        <div className="json-nested">
                            {keys.map((key, index) => (
                                <div key={key} className="json-item">
                                    <span className="json-key">"{key}"</span>: {renderValue(value[key], `${path}.${key}`, depth + 1)}
                                    {index < keys.length - 1 && ','}
                                </div>
                            ))}
                        </div>
                    )}
                    {!isExpanded && keys.length > 0 && <span className="json-ellipsis">...</span>}
                    {'}'}
                </span>
            );
        }

        return <span>{String(value)}</span>;
    };

    if (!data || data.length === 0) {
        return (
            <div className="json-result-viewer empty">
                <p>No results</p>
            </div>
        );
    }

    return (
        <div className="json-result-viewer">
            <div className="viewer-toolbar">
                <div className="view-mode-toggle">
                    <button
                        className={viewMode === 'pretty' ? 'active' : ''}
                        onClick={() => setViewMode('pretty')}
                    >
                        Pretty
                    </button>
                    <button
                        className={viewMode === 'compact' ? 'active' : ''}
                        onClick={() => setViewMode('compact')}
                    >
                        Compact
                    </button>
                </div>
                <div className="viewer-actions">
                    <button onClick={copyToClipboard} title="Copy to clipboard">
                        📋 Copy
                    </button>
                    <button onClick={downloadJSON} title="Download JSON">
                        💾 Download
                    </button>
                </div>
            </div>

            <div className={`json-content ${viewMode}`}>
                {viewMode === 'pretty' ? (
                    <div className="json-tree">
                        [
                        <div className="json-nested">
                            {data.map((item, index) => (
                                <div key={index} className="json-item">
                                    {renderValue(item, `root[${index}]`, 0)}
                                    {index < data.length - 1 && ','}
                                </div>
                            ))}
                        </div>
                        ]
                    </div>
                ) : (
                    <pre className="json-raw">
                        {JSON.stringify(data, null, 2)}
                    </pre>
                )}
            </div>
        </div>
    );
};
