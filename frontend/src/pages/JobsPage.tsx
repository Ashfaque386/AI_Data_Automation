import React, { useState, useEffect } from 'react';
import { jobsApi, Job, JobExecution } from '../services/jobsApi';
import { CreateJobModal } from '../components/CreateJobModal';
import { BackupWizard } from '../components/jobs/BackupWizard';
import './JobsPage.css';

export const JobsPage: React.FC = () => {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all');
    const [selectedJob, setSelectedJob] = useState<Job | null>(null);
    const [executionHistory, setExecutionHistory] = useState<JobExecution[]>([]);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showBackupWizard, setShowBackupWizard] = useState(false);
    const [activeExecutions, setActiveExecutions] = useState<Record<number, any>>({});
    const [jobToEdit, setJobToEdit] = useState<Job | null>(null);

    useEffect(() => {
        // Construct WS URL based on API config or current location
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
        const wsHost = baseUrl.replace(/^https?:\/\//, '');
        const wsUrl = `${wsProtocol}://${wsHost}/api/jobs/ws/status`;

        let ws: WebSocket | null = null;
        let reconnectTimer: any = null;

        const connect = () => {
            ws = new WebSocket(wsUrl);
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.active_jobs) {
                        const activeMap: Record<number, any> = {};
                        data.active_jobs.forEach((job: any) => {
                            activeMap[job.job_id] = job;
                        });
                        setActiveExecutions(activeMap);
                    }
                } catch (e) {
                    console.error('WS Error', e);
                }
            };
            ws.onclose = () => {
                reconnectTimer = setTimeout(connect, 3000);
            };
        };

        connect();
        return () => {
            if (ws) ws.close();
            if (reconnectTimer) clearTimeout(reconnectTimer);
        };
    }, []);

    useEffect(() => {
        fetchJobs();
    }, [filter]);

    const fetchJobs = async () => {
        try {
            setLoading(true);
            const response = await jobsApi.listJobs({ limit: 100 });
            setJobs(response.jobs || []);
            setError(null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load jobs');
        } finally {
            setLoading(false);
        }
    };

    const handleExecuteJob = async (jobId: number) => {
        try {
            await jobsApi.executeJob(jobId);
            // alert('Job execution started successfully'); // Removed alert for smoother UX
            fetchJobs();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to execute job');
        }
    };

    const handleStopJob = async (jobId: number, executionId: number) => {
        if (!confirm('Are you sure you want to stop this job?')) return;
        try {
            await jobsApi.cancelExecution(jobId, executionId);
            fetchJobs();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to stop job');
        }
    };

    const handleEditJob = (job: Job) => {
        setJobToEdit(job);
        setShowCreateModal(true);
    };

    const handleToggleJob = async (jobId: number) => {
        try {
            await jobsApi.toggleJob(jobId);
            fetchJobs();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to toggle job');
        }
    };

    const handleDeleteJob = async (jobId: number) => {
        if (!confirm('Are you sure you want to delete this job?')) return;

        try {
            await jobsApi.deleteJob(jobId);
            fetchJobs();
            setSelectedJob(null);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete job');
        }
    };

    const handleViewHistory = async (job: Job) => {
        setSelectedJob(job);
        try {
            const response = await jobsApi.listExecutions(job.id);
            setExecutionHistory(response.executions || []);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to load execution history');
        }
    };

    const handleDownloadBackup = async (jobId: number, executionId: number) => {
        try {
            // Use direct window navigation for download to avoid CORS/Blob issues
            // Construct URL using the same base URL logic as the API
            const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const token = localStorage.getItem('access_token');
            const downloadUrl = `${baseUrl}/api/jobs/${jobId}/executions/${executionId}/download?token=${token}`;

            // Open in new tab/window - this handles the file download naturally
            window.open(downloadUrl, '_blank');
        } catch (err: any) {
            console.error('Download error:', err);
            alert('Failed to initiate download. Please check console for details.');
        }
    };

    const getStatusBadge = (status: string) => {
        const statusMap: Record<string, string> = {
            pending: 'status-pending',
            running: 'status-running',
            completed: 'status-completed',
            failed: 'status-failed',
            cancelled: 'status-cancelled',
            retrying: 'status-retrying'
        };
        return statusMap[status.toLowerCase()] || 'status-pending';
    };

    const getJobTypeBadge = (jobType: string) => {
        const normalizedType = jobType.toLowerCase();
        const typeMap: Record<string, string> = {
            sql_script: 'SQL Script',
            stored_procedure: 'Stored Procedure',
            database_backup: 'Database Backup',
            data_import: 'Data Import',
            sql_query: 'SQL Query'
        };
        return typeMap[normalizedType] || jobType;
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    };

    const formatDuration = (ms?: number) => {
        if (!ms) return '-';
        const seconds = Math.floor(ms / 1000);
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h ${minutes % 60}m`;
    };

    const filteredJobs = jobs.filter(job => {
        if (filter === 'active') return job.is_active;
        if (filter === 'inactive') return !job.is_active;
        return true;
    });

    if (loading) {
        return <div className="jobs-page"><div className="loading">Loading jobs...</div></div>;
    }

    return (
        <div className="jobs-page">
            <div className="jobs-header">
                <h1>⏰ Jobs & Schedulers</h1>
                <div className="jobs-header-actions">
                    <button className="btn btn-secondary" onClick={() => setShowBackupWizard(true)}>
                        💾 Quick Backup
                    </button>
                    <button className="btn btn-primary" onClick={() => { setJobToEdit(null); setShowCreateModal(true); }}>
                        ➕ Create Job
                    </button>
                </div>
            </div>

            {error && <div className="error-banner">{error}</div>}

            <div className="jobs-tabs">
                <button
                    className={`tab ${filter === 'all' ? 'active' : ''}`}
                    onClick={() => setFilter('all')}
                >
                    All Jobs ({jobs.length})
                </button>
                <button
                    className={`tab ${filter === 'active' ? 'active' : ''}`}
                    onClick={() => setFilter('active')}
                >
                    Active ({jobs.filter(j => j.is_active).length})
                </button>
                <button
                    className={`tab ${filter === 'inactive' ? 'active' : ''}`}
                    onClick={() => setFilter('inactive')}
                >
                    Inactive ({jobs.filter(j => !j.is_active).length})
                </button>
            </div>

            <div className="jobs-content">
                <div className="jobs-list">
                    {filteredJobs.length === 0 ? (
                        <div className="empty-state">
                            <p>No jobs found</p>
                            <button className="btn btn-primary" onClick={() => { setJobToEdit(null); setShowCreateModal(true); }}>
                                Create Your First Job
                            </button>
                        </div>
                    ) : (
                        <div className="jobs-grid">
                            {filteredJobs.map(job => (
                                <div key={job.id} className="job-card">
                                    <div className="job-card-header">
                                        <div>
                                            <h3>{job.name}</h3>
                                            <span className={`badge ${getJobTypeBadge(job.job_type).replace(' ', '-').toLowerCase()}`}>
                                                {getJobTypeBadge(job.job_type)}
                                            </span>
                                        </div>
                                        <div className="job-card-status">
                                            {activeExecutions[job.id] ? (
                                                <span className="status-running" style={{ color: '#4a9eff', fontWeight: 'bold' }}>
                                                    ▶ Running
                                                </span>
                                            ) : job.is_active ? (
                                                <span className="status-active">● Active</span>
                                            ) : (
                                                <span className="status-inactive">○ Inactive</span>
                                            )}
                                        </div>
                                    </div>

                                    {job.description && (
                                        <p className="job-description">{job.description}</p>
                                    )}

                                    <div className="job-stats">
                                        <div className="stat">
                                            <span className="stat-label">Total Runs</span>
                                            <span className="stat-value">{job.run_count}</span>
                                        </div>
                                        <div className="stat">
                                            <span className="stat-label">Success</span>
                                            <span className="stat-value success">{job.success_count}</span>
                                        </div>
                                        <div className="stat">
                                            <span className="stat-label">Failed</span>
                                            <span className="stat-value failed">{job.failure_count}</span>
                                        </div>
                                    </div>

                                    <div className="job-schedule">
                                        {job.cron_expression ? (
                                            <>
                                                <div className="schedule-info">
                                                    <span className="label">Schedule:</span>
                                                    <code>{job.cron_expression}</code>
                                                </div>
                                                <div className="schedule-info">
                                                    <span className="label">Next Run:</span>
                                                    <span>{formatDate(job.next_run_at)}</span>
                                                </div>
                                            </>
                                        ) : (
                                            <div className="schedule-info">
                                                <span className="label">Manual execution only</span>
                                            </div>
                                        )}
                                        <div className="schedule-info">
                                            <span className="label">Last Run:</span>
                                            {activeExecutions[job.id] ? (
                                                <span style={{ color: '#4a9eff' }}>Started {formatDuration(Date.now() - new Date(activeExecutions[job.id].start_time).getTime())} ago</span>
                                            ) : (
                                                <span>{formatDate(job.last_run_at)}</span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="job-actions">
                                        {activeExecutions[job.id] ? (
                                            <button
                                                className="btn btn-sm btn-danger"
                                                onClick={() => handleStopJob(job.id, activeExecutions[job.id].execution_id)}
                                            >
                                                ⏹ Stop
                                            </button>
                                        ) : (
                                            <button
                                                className="btn btn-sm btn-primary"
                                                onClick={() => handleExecuteJob(job.id)}
                                                disabled={!job.is_active}
                                            >
                                                ▶ Run Now
                                            </button>
                                        )}
                                        {/* Download button for latest backup */}
                                        {job.job_type.toLowerCase() === 'database_backup' && job.last_execution && job.last_execution.result?.backup_filename && (
                                            <button
                                                className="btn btn-sm btn-secondary"
                                                onClick={() => handleDownloadBackup(job.id, job.last_execution!.id)}
                                                title="Download latest backup"
                                            >
                                                ⬇️ Download
                                            </button>
                                        )}
                                        <button
                                            className="btn btn-sm btn-secondary"
                                            onClick={() => handleViewHistory(job)}
                                        >
                                            📊 History
                                        </button>
                                        <button
                                            className="btn btn-sm btn-secondary"
                                            onClick={() => handleEditJob(job)}
                                        >
                                            ✏️ Edit
                                        </button>
                                        <button
                                            className="btn btn-sm btn-secondary"
                                            onClick={() => handleToggleJob(job.id)}
                                        >
                                            {job.is_active ? '⏸ Disable' : '▶ Enable'}
                                        </button>
                                        <button
                                            className="btn btn-sm btn-danger"
                                            onClick={() => handleDeleteJob(job.id)}
                                        >
                                            🗑 Delete
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {selectedJob && (
                    <div className="job-detail-panel">
                        <div className="panel-header">
                            <h2>Execution History: {selectedJob.name}</h2>
                            <button className="btn-close" onClick={() => setSelectedJob(null)}>✕</button>
                        </div>
                        <div className="executions-list">
                            {executionHistory.length === 0 ? (
                                <p className="empty-message">No executions yet</p>
                            ) : (
                                executionHistory.map((exec: JobExecution) => (
                                    <div key={exec.id} className="execution-item">
                                        <div className="execution-header">
                                            <span className={`status-badge ${getStatusBadge(exec.status)}`}>
                                                {exec.status}
                                            </span>
                                            <span className="execution-date">{formatDate(exec.created_at)}</span>
                                        </div>
                                        <div className="execution-details">
                                            <div className="detail">
                                                <span className="label">Duration:</span>
                                                <span>{formatDuration(exec.duration_ms)}</span>
                                            </div>
                                            <div className="detail">
                                                <span className="label">Rows Processed:</span>
                                                <span>{exec.rows_processed || 0}</span>
                                            </div>
                                            <div className="detail">
                                                <span className="label">Triggered By:</span>
                                                <span>{exec.triggered_by}</span>
                                            </div>
                                            {exec.retry_count > 0 && (
                                                <div className="detail">
                                                    <span className="label">Retries:</span>
                                                    <span>{exec.retry_count}</span>
                                                </div>
                                            )}
                                        </div>
                                        {exec.error_message && (
                                            <div className="execution-error">
                                                <strong>Error:</strong> {exec.error_message}
                                            </div>
                                        )}
                                        {selectedJob.job_type.toLowerCase() === 'database_backup' && exec.status.toLowerCase() === 'completed' && (
                                            <div className="execution-actions">
                                                <button
                                                    className="btn btn-sm btn-secondary"
                                                    onClick={() => handleDownloadBackup(selectedJob.id, exec.id)}
                                                >
                                                    ⬇️ Download Backup
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </div>

            <CreateJobModal
                isOpen={showCreateModal}
                job={jobToEdit}
                onClose={() => {
                    setShowCreateModal(false);
                    setJobToEdit(null);
                }}
                onJobCreated={() => {
                    setShowCreateModal(false);
                    setJobToEdit(null);
                    fetchJobs();
                }}
            />

            <BackupWizard
                isOpen={showBackupWizard}
                onClose={() => setShowBackupWizard(false)}
                onBackupCreated={() => {
                    setShowBackupWizard(false);
                    fetchJobs();
                }}
            />
        </div>
    );
};
