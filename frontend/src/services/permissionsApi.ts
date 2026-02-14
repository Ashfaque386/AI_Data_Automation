/**
 * Permissions API Service
 * Service layer for connection permission operations
 */
import api from './api';

export interface ConnectionPermission {
    id: number;
    connection_id: number;
    user_id: number;
    user_email: string;
    can_read: boolean;
    can_write: boolean;
    can_execute_ddl: boolean;
    allowed_schemas?: string[];
    denied_tables?: string[];
}

export interface PermissionGrantRequest {
    user_id: number;
    can_read: boolean;
    can_write: boolean;
    can_execute_ddl: boolean;
    allowed_schemas?: string[];
    denied_tables?: string[];
}

export const permissionsApi = {
    /**
     * Grant permission to a user for a connection
     */
    grantPermission: async (
        connectionId: number,
        request: PermissionGrantRequest
    ): Promise<ConnectionPermission> => {
        const response = await api.post(`/connections/${connectionId}/permissions`, request);
        return response.data;
    },

    /**
     * Revoke permission for a user on a connection
     */
    revokePermission: async (connectionId: number, userId: number): Promise<void> => {
        await api.delete(`/connections/${connectionId}/permissions/${userId}`);
    },

    /**
     * List all permissions for a connection
     */
    listConnectionPermissions: async (connectionId: number): Promise<ConnectionPermission[]> => {
        const response = await api.get(`/connections/${connectionId}/permissions`);
        return response.data;
    },

    /**
     * List all connection permissions for a user
     */
    listUserPermissions: async (userId: number): Promise<ConnectionPermission[]> => {
        const response = await api.get(`/users/${userId}/connection-permissions`);
        return response.data;
    }
};
