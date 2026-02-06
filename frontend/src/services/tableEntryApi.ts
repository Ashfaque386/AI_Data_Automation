/**
 * Table Entry API Service
 * Handles communication with table entry backend endpoints
 */
import { api } from './api'

const API_BASE = '/table-entry'

export interface ConnectionInfo {
    id: number
    name: string
    db_type: string
    host: string
    database: string
    is_active: boolean
}

export interface ColumnMetadata {
    name: string
    type: string
    nullable: boolean
    default: string | null
    is_primary_key: boolean
    is_foreign_key: boolean
    foreign_key_ref: {
        referenced_table: string
        referenced_column: string
    } | null
    is_unique: boolean
    autoincrement: boolean
}

export interface TableInfo {
    name: string
    schema: string
    row_count: number | null
}

export const tableEntryApi = {
    /**
     * Get list of available connections
     */
    async getConnections(): Promise<ConnectionInfo[]> {
        const response = await api.get(`${API_BASE}/connections`)
        return response.data.connections
    },

    /**
     * Get list of schemas for a connection
     */
    async getSchemas(connectionId: number): Promise<string[]> {
        const response = await api.get(`${API_BASE}/connections/${connectionId}/schemas`)
        return response.data.schemas
    },

    /**
     * Get list of tables in a schema
     */
    async getTables(connectionId: number, schema: string): Promise<TableInfo[]> {
        const response = await api.get(`${API_BASE}/connections/${connectionId}/tables`, {
            params: { schema }
        })
        return response.data.tables
    },

    /**
     * Get table schema metadata
     */
    async getTableSchema(connectionId: number, schema: string, table: string): Promise<{
        schema: string
        table: string
        columns: ColumnMetadata[]
        constraints: any
        stats: any
    }> {
        const response = await api.get(`${API_BASE}/connections/${connectionId}/schema/${schema}/${table}`)
        return response.data
    },

    /**
     * Validate rows before insert
     */
    async validateRows(
        connectionId: number,
        schema: string,
        table: string,
        rows: Array<Record<string, any>>
    ): Promise<any> {
        const response = await api.post(`${API_BASE}/validate`, {
            connection_id: connectionId,
            schema,
            table,
            rows
        })
        return response.data
    },

    /**
     * Insert rows into table
     */
    async insertRows(
        connectionId: number,
        schema: string,
        table: string,
        rows: Array<Record<string, any>>,
        mode: 'transaction' | 'row-by-row' = 'transaction'
    ): Promise<any> {
        const response = await api.post(`${API_BASE}/insert`, {
            connection_id: connectionId,
            schema,
            table,
            rows,
            mode
        })
        return response.data
    },

    /**
     * Get foreign key suggested values
     */
    async getForeignKeys(
        connectionId: number,
        schema: string,
        table: string,
        column: string,
        query?: string
    ): Promise<Array<{ value: any; label: string }>> {
        const response = await api.get(`${API_BASE}/connections/${connectionId}/reference/${schema}/${table}/${column}`, {
            params: { q: query }
        })
        return response.data.values
    },

    /**
     * Get audit logs
     */
    async getAuditLogs(limit: number = 100): Promise<any[]> {
        const response = await api.get(`${API_BASE}/audit`, {
            params: { limit }
        })
        return response.data.logs
    }
}

