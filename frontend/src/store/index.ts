import { create } from 'zustand'

interface User {
    id: number
    email: string
    username: string
    full_name: string | null
    is_superuser: boolean
    roles: any[]
}

interface AuthState {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    login: (email: string, password: string) => Promise<void>
    logout: () => void
    setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    isAuthenticated: !!localStorage.getItem('access_token'),
    isLoading: false,

    login: async (email, password) => {
        try {
            set({ isLoading: true })
            const { authApi } = await import('../services/api')
            const response = await authApi.login(email, password)

            localStorage.setItem('access_token', response.data.access_token)
            localStorage.setItem('refresh_token', response.data.refresh_token)

            const userResponse = await authApi.getCurrentUser()
            set({
                user: userResponse.data,
                isAuthenticated: true,
                isLoading: false,
            })
        } catch (error) {
            set({ isLoading: false })
            throw error
        }
    },

    logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, isAuthenticated: false })
    },

    setUser: (user) => set({ user }),
}))


interface AppState {
    activePage: string
    activeDataset: number | null
    sidebarCollapsed: boolean
    inspectorCollapsed: boolean
    bottomPanelCollapsed: boolean
    availableModels: string[]
    selectedModel: string | null
    isDbConfigured: boolean
    setActivePage: (page: string) => void
    setActiveDataset: (id: number | null) => void
    toggleSidebar: () => void
    toggleInspector: () => void
    toggleBottomPanel: () => void
    setAvailableModels: (models: string[]) => void
    setSelectedModel: (model: string) => void
    setIsDbConfigured: (status: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
    activePage: 'home',
    activeDataset: null,
    sidebarCollapsed: false,
    inspectorCollapsed: false,
    bottomPanelCollapsed: false,
    availableModels: [],
    selectedModel: null,
    isDbConfigured: false,

    setActivePage: (page) => set({ activePage: page }),
    setActiveDataset: (id) => set({ activeDataset: id }),
    toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    toggleInspector: () => set((state) => ({ inspectorCollapsed: !state.inspectorCollapsed })),
    toggleBottomPanel: () => set((state) => ({ bottomPanelCollapsed: !state.bottomPanelCollapsed })),
    setAvailableModels: (models) => set({ availableModels: models }),
    setSelectedModel: (model) => set({ selectedModel: model }),
    setIsDbConfigured: (status) => set({ isDbConfigured: status }),
}))
