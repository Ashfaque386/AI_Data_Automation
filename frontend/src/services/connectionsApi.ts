/**
 * Connections API Service
 * Handles all connection-related API calls
 */
import api from './api';

export interface Connection {
    id: number;
    name: string;
    description?: string;
    db_type: string;
    connection_group?: string;
    connection_mode?: string;
    host?: string;
    port?: number;
    database: string;
    username?: string;
    schema?: string;
    ssl_enabled: boolean;
    pool_size: number;
    max_connections: number;
    timeout_seconds: number;
    health_status?: string;
    last_health_check?: string;
    response_time_ms?: number;
    failed_attempts: number;
    capabilities?: any;
    is_active: boolean;
    is_read_only: boolean;
    is_default: boolean;
    created_at: string;
    has_connection_string?: boolean;
}

export interface ConnectionCreate {
    name: string;
    description?: string;
    db_type: string;
    connection_group?: string;
    connection_mode?: string;
    host?: string;
    port?: number;
    database: string;
    username?: string;
    password?: string;
    connection_string?: string;
    schema?: string;
    ssl_enabled?: boolean;
    ssl_cert_path?: string;
    pool_size?: number;
    max_connections?: number;
    timeout_seconds?: number;
    is_read_only?: boolean;
    is_default?: boolean;
}

export interface HealthCheckResult {
    connection_id: number;
    connection_name: string;
    status: string;
    is_healthy: boolean;
    response_time_ms?: number;
    last_check?: string;
}

export interface DatabaseDiscoveryRequest {
    db_type: string;
    host?: string;
    port?: number;
    username?: string;
    password?: string;
    connection_string?: string;
    schema?: string;
}

const connectionsApi = {
    // List all connections
    async listConnections(): Promise<Connection[]> {
        const response = await api.get('/connections/');
        return response.data;
    },

    // Get single connection
    async getConnection(id: number): Promise<Connection> {
        const response = await api.get(`/connections/${id}`);
        return response.data;
    },

    // Create connection
    async createConnection(data: ConnectionCreate): Promise<Connection> {
        const response = await api.post('/connections/', data);
        return response.data;
    },

    // Update connection
    async updateConnection(id: number, data: Partial<ConnectionCreate>): Promise<Connection> {
        const response = await api.put(`/connections/${id}`, data);
        return response.data;
    },

    // Delete connection
    async deleteConnection(id: number): Promise<void> {
        await api.delete(`/connections/${id}`);
    },

    // Discover databases
    async discoverDatabases(data: DatabaseDiscoveryRequest): Promise<string[]> {
        const response = await api.post('/connections/discover/databases', data);
        return response.data;
    },

    // Test connection
    async testConnection(id: number): Promise<HealthCheckResult> {
        const response = await api.post(`/connections/${id}/test`);
        return response.data;
    },

    // Activate connection
    async activateConnection(id: number): Promise<Connection> {
        const response = await api.post(`/connections/${id}/activate`);
        return response.data;
    },

    // Deactivate connection
    async deactivateConnection(id: number): Promise<Connection> {
        const response = await api.post(`/connections/${id}/deactivate`);
        return response.data;
    },

    // Get health status
    async getHealth(id: number): Promise<any> {
        const response = await api.get(`/connections/${id}/health`);
        return response.data;
    },

    // Get health history
    async getHealthHistory(id: number, hours: number = 24): Promise<any> {
        const response = await api.get(`/connections/${id}/health/history?hours=${hours}`);
        return response.data;
    },

    // Get health dashboard
    async getHealthDashboard(): Promise<any> {
        const response = await api.get('/connections/health/dashboard');
        return response.data;
    },

    // Get capabilities
    async getCapabilities(id: number, refresh: boolean = false): Promise<any> {
        const response = await api.get(`/connections/${id}/capabilities?refresh=${refresh}`);
        return response.data;
    },

    // List schemas
    async listSchemas(id: number): Promise<any> {
        const response = await api.get(`/connections/${id}/schemas`);
        return response.data;
    },

    // List tables
    async listTables(id: number, schema: string = 'public'): Promise<any> {
        const response = await api.get(`/connections/${id}/tables?schema=${schema}`);
        return response.data;
    },
};

export default connectionsApi;
