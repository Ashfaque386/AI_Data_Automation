/**
 * MongoDB Query Interface Component
 * UI for building and executing MongoDB queries
 */
import React, { useState, useEffect } from 'react';
import { mongodbApi, MongoDBQueryRequest, MongoDBCollection } from '../../services/mongodbApi';
import { JSONResultViewer } from './JSONResultViewer';
import './MongoDBQueryInterface.css';

interface MongoDBQueryInterfaceProps {
    connectionId: number;
    connectionName: string;
    onClose: () => void;
}

export const MongoDBQueryInterface: React.FC<MongoDBQueryInterfaceProps> = ({
    connectionId,
    connectionName,
    onClose
}) => {
    const [collections, setCollections] = useState<MongoDBCollection[]>([]);
    const [selectedCollection, setSelectedCollection] = useState<string>('');
    const [operation, setOperation] = useState<'find' | 'aggregate' | 'count' | 'distinct'>('find');
    const [filterJson, setFilterJson] = useState<string>('{}');
    const [projectionJson, setProjectionJson] = useState<string>('');
    const [limit, setLimit] = useState<number>(100);
    const [pipelineJson, setPipelineJson] = useState<string>('[]');
    const [distinctField, setDistinctField] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<any>(null);

    useEffect(() => {
        loadCollections();
    }, [connectionId]);

    const loadCollections = async () => {
        try {
            const colls = await mongodbApi.listCollections(connectionId);
            setCollections(colls);
            if (colls.length > 0) {
                setSelectedCollection(colls[0].name);
            }
        } catch (err: any) {
            console.error('Failed to load collections:', err);
            setError('Failed to load collections');
        }
    };

    const handleExecuteQuery = async () => {
        if (!selectedCollection) {
            setError('Please select a collection');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const query: MongoDBQueryRequest = {
                collection: selectedCollection,
                operation: operation
            };

            if (operation === 'find') {
                query.filter = filterJson ? JSON.parse(filterJson) : {};
                query.projection = projectionJson ? JSON.parse(projectionJson) : undefined;
                query.limit = limit;
            } else if (operation === 'aggregate') {
                query.pipeline = JSON.parse(pipelineJson);
            } else if (operation === 'count') {
                query.filter = filterJson ? JSON.parse(filterJson) : {};
            } else if (operation === 'distinct') {
                query.field = distinctField;
                query.filter = filterJson ? JSON.parse(filterJson) : {};
            }

            const queryResult = await mongodbApi.executeQuery(connectionId, query);
            setResult(queryResult);
        } catch (err: any) {
            console.error('Query execution failed:', err);
            setError(err.response?.data?.detail || err.message || 'Query execution failed');
        } finally {
            setLoading(false);
        }
    };

    const insertExample = (exampleType: string) => {
        if (exampleType === 'find-filter') {
            setFilterJson('{"age": {"$gt": 18}, "status": "active"}');
        } else if (exampleType === 'find-projection') {
            setProjectionJson('{"name": 1, "email": 1, "_id": 0}');
        } else if (exampleType === 'aggregate') {
            setPipelineJson(JSON.stringify([
                { "$match": { "status": "active" } },
                { "$group": { "_id": "$category", "count": { "$sum": 1 } } },
                { "$sort": { "count": -1 } }
            ], null, 2));
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content mongodb-query-interface" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>🍃 MongoDB Query Builder</h2>
                    <p className="subtitle">Connection: {connectionName}</p>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    <div className="query-builder">
                        <div className="form-row">
                            <div className="form-group">
                                <label>Collection</label>
                                <select
                                    value={selectedCollection}
                                    onChange={(e) => setSelectedCollection(e.target.value)}
                                    disabled={loading}
                                >
                                    {collections.map(coll => (
                                        <option key={coll.name} value={coll.name}>
                                            {coll.name} ({coll.row_count?.toLocaleString() || 0} docs)
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Operation</label>
                                <div className="operation-tabs">
                                    <button
                                        className={`tab-btn ${operation === 'find' ? 'active' : ''}`}
                                        onClick={() => setOperation('find')}
                                    >
                                        Find
                                    </button>
                                    <button
                                        className={`tab-btn ${operation === 'aggregate' ? 'active' : ''}`}
                                        onClick={() => setOperation('aggregate')}
                                    >
                                        Aggregate
                                    </button>
                                    <button
                                        className={`tab-btn ${operation === 'count' ? 'active' : ''}`}
                                        onClick={() => setOperation('count')}
                                    >
                                        Count
                                    </button>
                                    <button
                                        className={`tab-btn ${operation === 'distinct' ? 'active' : ''}`}
                                        onClick={() => setOperation('distinct')}
                                    >
                                        Distinct
                                    </button>
                                </div>
                            </div>
                        </div>

                        {operation === 'find' && (
                            <div className="operation-params">
                                <div className="form-group">
                                    <label>
                                        Filter (JSON)
                                        <button className="example-btn" onClick={() => insertExample('find-filter')}>
                                            Example
                                        </button>
                                    </label>
                                    <textarea
                                        value={filterJson}
                                        onChange={(e) => setFilterJson(e.target.value)}
                                        placeholder='{"field": "value"}'
                                        rows={4}
                                        disabled={loading}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>
                                        Projection (JSON, optional)
                                        <button className="example-btn" onClick={() => insertExample('find-projection')}>
                                            Example
                                        </button>
                                    </label>
                                    <textarea
                                        value={projectionJson}
                                        onChange={(e) => setProjectionJson(e.target.value)}
                                        placeholder='{"field1": 1, "field2": 1}'
                                        rows={3}
                                        disabled={loading}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Limit</label>
                                    <input
                                        type="number"
                                        value={limit}
                                        onChange={(e) => setLimit(parseInt(e.target.value))}
                                        min={1}
                                        max={1000}
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                        )}

                        {operation === 'aggregate' && (
                            <div className="operation-params">
                                <div className="form-group">
                                    <label>
                                        Pipeline (JSON Array)
                                        <button className="example-btn" onClick={() => insertExample('aggregate')}>
                                            Example
                                        </button>
                                    </label>
                                    <textarea
                                        value={pipelineJson}
                                        onChange={(e) => setPipelineJson(e.target.value)}
                                        placeholder='[{"$match": {...}}, {"$group": {...}}]'
                                        rows={8}
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                        )}

                        {operation === 'count' && (
                            <div className="operation-params">
                                <div className="form-group">
                                    <label>Filter (JSON)</label>
                                    <textarea
                                        value={filterJson}
                                        onChange={(e) => setFilterJson(e.target.value)}
                                        placeholder='{"field": "value"}'
                                        rows={4}
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                        )}

                        {operation === 'distinct' && (
                            <div className="operation-params">
                                <div className="form-group">
                                    <label>Field Name</label>
                                    <input
                                        type="text"
                                        value={distinctField}
                                        onChange={(e) => setDistinctField(e.target.value)}
                                        placeholder="fieldName"
                                        disabled={loading}
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Filter (JSON, optional)</label>
                                    <textarea
                                        value={filterJson}
                                        onChange={(e) => setFilterJson(e.target.value)}
                                        placeholder='{"field": "value"}'
                                        rows={3}
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                        )}

                        <div className="query-actions">
                            <button
                                className="btn btn-primary"
                                onClick={handleExecuteQuery}
                                disabled={loading}
                            >
                                {loading ? 'Executing...' : '▶ Execute Query'}
                            </button>
                        </div>
                    </div>

                    {result && (
                        <div className="query-results">
                            <div className="results-header">
                                <h3>Results</h3>
                                <span className="results-meta">
                                    {result.row_count} documents • {result.execution_time_ms}ms
                                </span>
                            </div>
                            <JSONResultViewer data={result.data} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
