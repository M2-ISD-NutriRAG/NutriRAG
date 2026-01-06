import { apiClient } from '@/lib/api'
import type { ChatMessage, ChatRequest, ChatResponse } from '@shared/types'

// Re-export pour compatibilité
export type { ChatMessage, ChatRequest, ChatResponse }

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    // const response = await apiClient.post('/api/orchestrate', request)
    // return response.data

    const response = await apiClient.post('/api/chat/send', request)
    return response.data
  },

  async getConversationMessages(conversationId: string): Promise<any> {
    const response = await apiClient.get(`/api/chat/conversations/${conversationId}/messages`)
    if (!response.data) {
      throw new Error('No messages found for this conversation')
    }
    return response.data
  },

  async getConversations(): Promise<any> {
    const response = await apiClient.get('/api/chat/conversations')
    // STOPPED HERE
    return response.data
  },

  async createConversation(): Promise<{ id: string, title: string }> {
    const response = await apiClient.post('/api/chat/conversations', {})
    return response.data
  },

  async detectIntent(message: string): Promise<{ intent: string; confidence: number }> {
    const response = await apiClient.post('/api/orchestrate/intent', { message })
    return response.data
  },

  async deleteConversation(conversationId: string): Promise<void> {
    await apiClient.delete(`/api/chat/conversations/${conversationId}`);
  }
}

export default chatService

