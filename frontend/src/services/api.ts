import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
    baseURL: `${API_BASE_URL}/api`,
})

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// Response interceptor for token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken) {
                try {
                    const { data } = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
                        refresh_token: refreshToken,
                    })

                    localStorage.setItem('access_token', data.access_token)
                    localStorage.setItem('refresh_token', data.refresh_token)

                    originalRequest.headers.Authorization = `Bearer ${data.access_token}`
                    return api(originalRequest)
                } catch {
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/login'
                }
            }
        }

        return Promise.reject(error)
    }
)

// Auth API
export const authApi = {
    login: (email: string, password: string) =>
        api.post('/auth/login', { email, password }),

    register: (data: any) =>
        api.post('/auth/register', data),

    logout: () =>
        api.post('/auth/logout'),

    getCurrentUser: () =>
        api.get('/auth/me'),
}

// Datasets API
export const datasetsApi = {
    list: () =>
        api.get('/datasets/', { params: { _t: Date.now() } }),

    get: (id: number) =>
        api.get(`/datasets/${id}`),

    upload: (file: File) => {
        const formData = new FormData()
        formData.append('file', file)
        return api.post('/datasets/upload', formData, {
            params: { name: file.name }
        })
    },

    getData: (id: number, params: any) =>
        api.post(`/datasets/${id}/data`, params),

    delete: (id: number) =>
        api.delete(`/datasets/${id}`),

    getVersions: (id: number) =>
        api.get(`/datasets/${id}/versions`),
}

// SQL API
export const sqlApi = {
    execute: (query: string, limit?: number, source?: string) =>
        api.post('/sql/execute', { query, limit, source }),

    explain: (query: string) =>
        api.post('/sql/explain', { query }),

    getHistory: (limit?: number, savedOnly?: boolean) =>
        api.get('/sql/history', { params: { limit, saved_only: savedOnly } }),

    saveQuery: (queryId: number, name: string) =>
        api.post(`/sql/history/${queryId}/save`, { name }),

    getTables: () =>
        api.get('/sql/tables'),
}

// Export API
export const exportApi = {
    toExcel: (datasetId: number) =>
        api.get(`/export/excel/${datasetId}`, { responseType: 'blob' }),

    toCsv: (datasetId: number) =>
        api.get(`/export/csv/${datasetId}`, { responseType: 'blob' }),

    toJson: (datasetId: number) =>
        api.get(`/export/json/${datasetId}`, { responseType: 'blob' }),
}

// AI API
// AI API
export const aiApi = {
    // Legacy compatible - defaults to ollama if not specified
    getModels: (provider: string = 'ollama', apiKey?: string, apiUrl?: string) =>
        api.get('/ai/models', { params: { provider, api_key: apiKey, api_url: apiUrl } }),

    getProviders: () =>
        api.get('/ai/providers'),

    getConfig: () =>
        api.get('/ai/config'),

    getActiveConfig: () =>
        api.get('/ai/config/active'),

    saveConfig: (config: any) =>
        api.post('/ai/config', config),

    testConnection: (config: any) =>
        api.post('/ai/test', config),

    nlToSql: (query: string, datasetIds?: number[], model?: string) =>
        api.post('/ai/nl-to-sql', { query, dataset_ids: datasetIds, model }),

    suggestFormula: (description: string, datasetId: number, model?: string) =>
        api.post('/ai/suggest-formula', { description, dataset_id: datasetId, model }),

    checkQuality: (datasetId: number, model?: string) =>
        api.post('/ai/quality-check', { dataset_id: datasetId, model }),
}

// Setup API
export const setupApi = {
    getStatus: () =>
        api.get('/setup/status'),

    testConnection: (config: any) =>
        api.post('/setup/test-connection', config),

    configure: (config: any) =>
        api.post('/setup/configure', config),
}

export default api
