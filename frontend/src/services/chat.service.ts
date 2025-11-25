import { apiClient } from "@/lib/api";
import type { ChatMessage, ChatRequest, ChatResponse } from "@shared/types";

// Re-export pour compatibilité
export type { ChatMessage, ChatRequest, ChatResponse };

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post("/api/orchestrate", request);
    return response.data;
  },

  async detectIntent(
    message: string,
  ): Promise<{ intent: string; confidence: number }> {
    const response = await apiClient.post("/api/orchestrate/intent", {
      message,
    });
    return response.data;
  },
};

export default chatService;
