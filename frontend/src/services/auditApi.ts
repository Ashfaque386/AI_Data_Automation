/**
 * Audit Logs API Service
 * Service layer for audit log operations
 */
import api from './api';

export interface AuditLog {
    id: number;
    timestamp: string;
    user_id?: number;
    user_email?: string;
    connection_id?: number;
    connection_name?: string;
    action: string;
    action_type?: string;
    resource_type: string;
    resource_id?: string;
    resource_name?: string;
    details?: any;
    query_text?: string;
    ip_address?: string;
    user_agent?: string;
    status: string;
    error_message?: string;
    duration_ms?: number;
    rows_affected?: number;
}

export interface AuditStats {
    total_actions: number;
    successful_actions: number;
    failed_actions: number;
    success_rate: number;
    action_breakdown: Record<string, number>;
}

export interface AuditLogsParams {
    user_id?: number;
    connection_id?: number;
    action_type?: string;
    resource_type?: string;
    start_date?: string;
    end_date?: string;
    success_only?: boolean;
    limit?: number;
    offset?: number;
}

export const auditApi = {
    /**
     * Get audit logs with optional filters
     */
    getLogs: async (params: AuditLogsParams = {}): Promise<AuditLog[]> => {
        const response = await api.get('/audit/logs', { params });
        return response.data;
    },

    /**
     * Get a specific audit log by ID
     */
    getLog: async (logId: number): Promise<AuditLog> => {
        const response = await api.get(`/audit/logs/${logId}`);
        return response.data;
    },

    /**
     * Get audit statistics
     */
    getStats: async (params: { user_id?: number; connection_id?: number; days?: number } = {}): Promise<AuditStats> => {
        const response = await api.get('/audit/stats', { params });
        return response.data;
    },

    /**
     * Export audit logs
     */
    exportLogs: async (format: 'csv' | 'json', params: AuditLogsParams = {}): Promise<Blob> => {
        const response = await api.get('/audit/export', {
            params: { ...params, format },
            responseType: 'blob'
        });
        return response.data;
    }
};
