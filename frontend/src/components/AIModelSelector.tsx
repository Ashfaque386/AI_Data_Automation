import React, { useEffect } from 'react'
import { useAppStore } from '../store'
import { aiApi } from '../services/api'
import './AIModelSelector.css'

export const AIModelSelector: React.FC = () => {
    const { availableModels, selectedModel, setAvailableModels, setSelectedModel } = useAppStore()

    useEffect(() => {
        const initializeConfig = async () => {
            try {
                // 1. Get the active configuration first
                const configRes = await aiApi.getActiveConfig()

                let provider = 'ollama' // Default
                let savedModel = ''

                if (configRes.data) {
                    provider = configRes.data.provider
                    savedModel = configRes.data.model_name
                }

                // 2. Fetch models for the ACTIVE provider
                // Backend list_models will use saved key if api_key omitted
                const modelsRes = await aiApi.getModels(provider)
                let models = modelsRes.data.models

                // Ensure saved model is in the list
                if (savedModel && !models.includes(savedModel)) {
                    models = [savedModel, ...models]
                }

                setAvailableModels(models)

                // 3. Set selected model
                // Priority: Saved Config Model > Current Store Value > First Available
                if (savedModel) {
                    setSelectedModel(savedModel)
                } else if (!selectedModel && models.length > 0) {
                    setSelectedModel(models[0])
                }

            } catch (error) {
                console.error('Failed to initialize AI models:', error)
            }
        }

        initializeConfig()
    }, [setAvailableModels, setSelectedModel]) // Remove selectedModel from deps to prevent loops

    if (availableModels.length === 0) {
        return null
    }

    return (
        <div className="ai-model-selector">
            <label htmlFor="ai-model">🤖 AI Model:</label>
            <select
                id="ai-model"
                value={selectedModel || ''}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="model-select"
            >
                {availableModels.map((model) => (
                    <option key={model} value={model}>
                        {model}
                    </option>
                ))}
            </select>
        </div>
    )
}
