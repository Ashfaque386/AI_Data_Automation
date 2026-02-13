/**
 * Jobs API Service
 * API client for Jobs & Schedulers endpoints
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';

// Create axios instance with auth
const api = axios.create({
    baseURL: API_BASE_URL,
});

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                try {
                    const { data } = await axios.post('http://localhost:8000/api/auth/refresh', {
                        refresh_token: refreshToken,
                    });

                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);

                    originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
                    return api(originalRequest);
                } catch {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    window.location.href = '/login';
                }
            }
        }

        return Promise.reject(error);
    }
);

// Job Types
export interface Job {
    id: number;
    name: string;
    description?: string;
    job_type: string;
    is_active: boolean;
    cron_expression?: string;
    timezone: string;
    last_run_at?: string;
    next_run_at?: string;
    run_count: number;
    success_count: number;
    failure_count: number;
    consecutive_failures: number;
    created_at: string;
    last_execution?: {
        id: number;
        status: string;
        result?: any;
    };
}

export interface JobExecution {
    id: number;
    status: string;
    started_at?: string;
    completed_at?: string;
    duration_ms?: number;
    rows_processed?: number;
    rows_affected?: number;
    error_message?: string;
    triggered_by: string;
    retry_count: number;
    created_at: string;
    result?: any;
}

export interface CreateJobRequest {
    name: string;
    description?: string;
    job_type: string;
    connection_id: number;
    target_schema?: string;
    cron_expression?: string;
    timezone?: string;
    is_active?: boolean;
    config: any;
    pre_execution_sql?: string;
    post_execution_sql?: string;
    retry_policy?: any;
    max_runtime_seconds?: number;
    failure_threshold?: number;
    notify_on_success?: boolean;
    notify_on_failure?: boolean;
    notification_emails?: string[];
}

// API Functions

export const jobsApi = {
    // Job CRUD
    async listJobs(filters?: { job_type?: string; is_active?: boolean; limit?: number; offset?: number }) {
        const response = await api.get('/jobs', { params: filters });
        return response.data;
    },

    async getJob(jobId: number) {
        const response = await api.get(`/jobs/${jobId}`);
        return response.data;
    },

    async createJob(data: CreateJobRequest) {
        const response = await api.post('/jobs', data);
        return response.data;
    },

    async updateJob(jobId: number, data: Partial<CreateJobRequest>) {
        const response = await api.put(`/jobs/${jobId}`, data);
        return response.data;
    },

    async deleteJob(jobId: number) {
        const response = await api.delete(`/jobs/${jobId}`);
        return response.data;
    },

    async toggleJob(jobId: number) {
        const response = await api.patch(`/jobs/${jobId}/toggle`);
        return response.data;
    },

    // Job Execution
    async executeJob(jobId: number) {
        const response = await api.post(`/jobs/${jobId}/execute`);
        return response.data;
    },

    async cancelExecution(jobId: number, executionId: number) {
        const response = await api.post(`/jobs/${jobId}/cancel`, null, { params: { execution_id: executionId } });
        return response.data;
    },

    // Job History
    async listExecutions(jobId: number, limit = 50, offset = 0) {
        const response = await api.get(`/jobs/${jobId}/executions`, { params: { limit, offset } });
        return response.data;
    },

    async getExecutionDetails(jobId: number, executionId: number) {
        const response = await api.get(`/jobs/${jobId}/executions/${executionId}`);
        return response.data;
    },

    async downloadBackup(jobId: number, executionId: number) {
        const url = `/jobs/${jobId}/executions/${executionId}/download`;
        console.log('Requesting download from:', `${api.defaults.baseURL}${url}`);
        const response = await api.get(url, {
            responseType: 'blob'
        });
        return response.data;
    },

    async getExecutionLogs(jobId: number, executionId: number) {
        const response = await api.get(`/jobs/${jobId}/executions/${executionId}/logs`);
        return response.data;
    },

    // Stored Procedures
    async discoverProcedures(connectionId: number, schema = 'public') {
        const response = await api.get('/jobs/procedures/discover', { params: { connection_id: connectionId, schema } });
        return response.data;
    },

    async getProcedureParameters(procedureName: string, connectionId: number, schema = 'public') {
        const response = await api.get(`/jobs/procedures/${procedureName}/parameters`, {
            params: { connection_id: connectionId, schema }
        });
        return response.data;
    },

    // Quick Backup
    async quickBackup(data: {
        connection_id: number;
        database_name: string;
        backup_type?: string;
        compression_enabled?: boolean;
        retention_days?: number;
        storage_path?: string;
        format?: string;
    }) {
        const response = await api.post('/jobs/backup/quick', data);
        return response.data;
    },

    // Schedule Management
    async previewNextRuns(jobId: number, count = 5) {
        const response = await api.get(`/jobs/${jobId}/schedule/next-runs`, { params: { count } });
        return response.data;
    },

    async validateCron(cronExpression: string) {
        const response = await api.post('/jobs/schedule/validate', null, { params: { cron_expression: cronExpression } });
        return response.data;
    },

    async getCronPresets() {
        const response = await api.get('/jobs/schedule/presets');
        return response.data;
    },

    async getConnections() {
        const response = await api.get('/connections');
        return response.data;
    },

    // System
    async listDirectories(path?: string) {
        const response = await api.get('/jobs/system/directories', { params: { path } });
        return response.data;
    },
};
