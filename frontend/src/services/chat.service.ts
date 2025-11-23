import { apiClient } from '@/lib/api'
import type {OrchestrationRequest, OrchestrationResponse } from '@shared/types'

// Re-export pour compatibilité
export type {OrchestrationRequest, OrchestrationResponse }

export const chatService = {
  async sendMessage(request: OrchestrationRequest): Promise<OrchestrationResponse> {
    const response = await apiClient.post('/api/orchestrate', request)
    return response.data
  },

  async detectIntent(message: string): Promise<{ intent: string; confidence: number }> {
    const response = await apiClient.post('/api/orchestrate/intent', { message })
    return response.data
  },
}

export default chatService

