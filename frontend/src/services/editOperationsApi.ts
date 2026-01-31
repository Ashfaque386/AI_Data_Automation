/**
 * Edit Operations API Service
 * 
 * Handles all dataset editing operations including:
 * - Session management (lock/unlock)
 * - Cell, row, and column operations
 * - Change tracking and commit/discard
 */

import { api } from './api'

export interface CellChange {
    row_index: number
    column_name: string
    old_value: any
    new_value: any
}

export interface LockResponse {
    session_id: string
    locked_at: string
    expires_at: string
    dataset_id: number
    user_id: number
}

export interface LockStatusResponse {
    locked: boolean
    session_id?: string
    user_id?: number
    locked_at?: string
    expires_at?: string
}

export interface ChangeHistoryItem {
    id: number
    change_type: string
    row_index?: number
    column_name?: string
    old_value: any
    new_value: any
    timestamp: string
    is_committed: boolean
}

export const editOperationsApi = {
    // Lock Management
    lockDataset: async (datasetId: number, timeoutMinutes: number = 30): Promise<LockResponse> => {
        const { data } = await api.post(`/datasets/${datasetId}/lock`, {
            timeout_minutes: timeoutMinutes
        })
        return data
    },

    unlockDataset: async (datasetId: number, sessionId: string): Promise<void> => {
        await api.delete(`/datasets/${datasetId}/lock`, {
            data: { session_id: sessionId }
        })
    },

    getLockStatus: async (datasetId: number): Promise<LockStatusResponse> => {
        const { data } = await api.get(`/datasets/${datasetId}/lock-status`)
        return data
    },

    forceUnlock: async (datasetId: number): Promise<{ message: string }> => {
        const { data } = await api.post(`/datasets/${datasetId}/lock/force-unlock`)
        return data
    },

    // Cell Operations
    updateCells: async (datasetId: number, sessionId: string, changes: CellChange[]): Promise<void> => {
        await api.post(`/datasets/${datasetId}/cells/update`, {
            session_id: sessionId,
            changes
        })
    },

    // Row Operations
    addRow: async (datasetId: number, sessionId: string, position: number, data: Record<string, any>): Promise<void> => {
        await api.post(`/datasets/${datasetId}/rows`, {
            session_id: sessionId,
            position,
            data
        })
    },

    deleteRows: async (datasetId: number, sessionId: string, rowIndices: number[]): Promise<void> => {
        await api.delete(`/datasets/${datasetId}/rows`, {
            data: {
                session_id: sessionId,
                row_indices: rowIndices
            }
        })
    },

    // Column Operations
    addColumn: async (datasetId: number, sessionId: string, name: string, dataType: string = 'string', defaultValue: any = null): Promise<void> => {
        await api.post(`/datasets/${datasetId}/columns`, {
            session_id: sessionId,
            name,
            data_type: dataType,
            default_value: defaultValue
        })
    },

    deleteColumn: async (datasetId: number, sessionId: string, columnName: string): Promise<void> => {
        await api.delete(`/datasets/${datasetId}/columns/${columnName}`, {
            data: { session_id: sessionId }
        })
    },

    // Change Management
    commitChanges: async (datasetId: number, sessionId: string): Promise<{ changes_committed: number }> => {
        const { data } = await api.post(`/datasets/${datasetId}/changes/commit`, {
            session_id: sessionId
        })
        return data
    },

    discardChanges: async (datasetId: number, sessionId: string): Promise<{ changes_discarded: number }> => {
        const { data } = await api.post(`/datasets/${datasetId}/changes/discard`, {
            session_id: sessionId
        })
        return data
    },

    getChangeHistory: async (datasetId: number, limit: number = 100, committedOnly: boolean = true): Promise<ChangeHistoryItem[]> => {
        const { data } = await api.get(`/datasets/${datasetId}/changes/history`, {
            params: { limit, committed_only: committedOnly }
        })
        return data
    },

    getUncommittedChanges: async (datasetId: number, sessionId: string): Promise<{ count: number; changes: ChangeHistoryItem[] }> => {
        const { data } = await api.get(`/datasets/${datasetId}/changes/uncommitted`, {
            params: { session_id: sessionId }
        })
        return data
    }
}
