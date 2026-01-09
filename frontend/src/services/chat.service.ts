import { apiClient } from '@/lib/api'
import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  StreamingChatMessage,
  StreamChunk,
  StreamingCallbacks,
  ThinkingStatus
} from '@shared/types'

// Re-export pour compatibilité
export type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  StreamingChatMessage,
  StreamChunk,
  StreamingCallbacks,
  ThinkingStatus
}

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
  },

  // Streaming chat methods
  async sendMessageStream(
    request: ChatRequest,
    callbacks: StreamingCallbacks
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('snowflake_token');
      if (!token) {
        reject(new Error('No authentication token found'));
        return;
      }

      // Use fetch API for POST with streaming SSE response
      const url = new URL('/api/chat/send-stream', apiClient.defaults.baseURL);
      fetch(url.toString(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/plain',
        },
        body: JSON.stringify(request),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body reader available');
        }

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();

              if (done) {
                resolve();
                break;
              }

              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data: StreamChunk = JSON.parse(line.slice(6));
                    this.handleStreamChunk(data, callbacks);
                  } catch (parseError) {
                    console.warn('Failed to parse stream chunk:', line, parseError);
                  }
                }
              }
            }
          } catch (streamError) {
            reject(streamError);
          }
        };

        processStream();
      })
      .catch(error => {
        reject(error);
      });
    });
  },

  handleStreamChunk(chunk: StreamChunk, callbacks: StreamingCallbacks): void {
    switch (chunk.type) {
      case 'conversation_id':
        if (chunk.conversation_id && callbacks.onConversationId) {
          callbacks.onConversationId(chunk.conversation_id);
        }
        break;

      case 'thinking':
        if (chunk.status && chunk.message && callbacks.onThinking) {
          callbacks.onThinking({
            status: chunk.status,
            message: chunk.message
          });
        }
        break;

      case 'text_delta':
        // Only process incremental deltas from text.delta events
        if (chunk.text && chunk.event === 'response.text.delta' && callbacks.onTextDelta) {
          callbacks.onTextDelta(chunk.text);
        }
        break;

      case 'complete_response':
        // Only process complete responses from response.text events
        if (chunk.text && chunk.event === 'response.text' && callbacks.onCompleteResponse) {
          callbacks.onCompleteResponse(chunk.text);
        }
        break;

      case 'tool_status':
        if (chunk.status && chunk.message && callbacks.onToolStatus) {
          callbacks.onToolStatus(chunk.status, chunk.message, chunk.tool_type);
        }
        break;

      case 'tool_use':
        if (chunk.tool_name && chunk.tool_input && chunk.tool_use_id && callbacks.onToolUse) {
          callbacks.onToolUse(chunk.tool_name, chunk.tool_input, chunk.tool_use_id);
        }
        break;

      case 'done':
        if (callbacks.onDone) {
          callbacks.onDone();
        }
        break;

      case 'error':
        if (chunk.message && callbacks.onError) {
          callbacks.onError(chunk.message);
        }
        break;

      default:
        console.warn('Unknown stream chunk type:', chunk.type);
    }
  }
}

export default chatService
