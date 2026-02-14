/**
 * MongoDB API Service
 * Service layer for MongoDB query operations
 */
import api from './api';

export interface MongoDBQueryRequest {
    collection: string;
    operation: 'find' | 'aggregate' | 'count' | 'distinct';
    filter?: Record<string, any>;
    projection?: Record<string, any>;
    limit?: number;
    skip?: number;
    sort?: Record<string, number>;
    pipeline?: any[];
    field?: string;
}

export interface MongoDBQueryResult {
    status: string;
    data: any[];
    columns: string[];
    row_count: number;
    execution_time_ms: number;
    collection: string;
    operation: string;
}

export interface MongoDBCollection {
    name: string;
    row_count: number;
    size_bytes: number;
}

export const mongodbApi = {
    /**
     * Execute MongoDB query
     */
    executeQuery: async (
        connectionId: number,
        query: MongoDBQueryRequest
    ): Promise<MongoDBQueryResult> => {
        const response = await api.post(`/connections/${connectionId}/mongodb/query`, query);
        return response.data;
    },

    /**
     * List MongoDB collections
     */
    listCollections: async (connectionId: number): Promise<MongoDBCollection[]> => {
        const response = await api.get(`/connections/${connectionId}/mongodb/collections`);
        return response.data.collections;
    }
};

export default mongodbApi;
