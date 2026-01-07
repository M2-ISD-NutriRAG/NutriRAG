/**
 * Shared type definitions for Orchestration
 */

export interface OrchestrationRequest {
  user_query: string
  context?: Record<string, any>
  user_profile?: Record<string, any>  // Backend utilise Dict[str, Any]
}

export interface AgentStep {
  agent: string  // Backend: str (pas d'enum)
  action: string
  input: Record<string, any>
  output: Record<string, any>
  success: boolean
  execution_time_ms: number
}

export interface OrchestrationResponse {
  steps: AgentStep[]
  final_result: Record<string, any>
  intent_detected: string  // Backend: str (pas d'enum)
  total_execution_time_ms: number
  success: boolean
  message?: string
}

// ============================================
// Types additionnels pour le Frontend (pas dans backend)
// ============================================

// UserProfile structuré pour le frontend
export interface UserProfile {
  intolerances?: string[]  // ["lactose", "gluten", "nuts"]
  preferences?: string[]   // ["vegetarian", "low-carb"]
  goals?: string[]         // ["weight-loss", "muscle-gain"]
}

// Intent types pour le frontend
export type Intent = 'search' | 'transform' | 'recipe_detail' | 'analytics' | 'multi_step' | 'profile_update'

// Chat types pour le frontend
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: {
    intent?: string
    data?: any
  }
}

export interface ChatRequest {
  message: string
  conversation_history?: ChatMessage[]
  user_profile?: UserProfile
  current_recipe_id?: string
  conversation_id?: string
}

export interface ChatResponse {
  message: string
  intent: string
  data?: any
  suggestions?: string[]
  conversation_id?: string
}

// Streaming types
export interface StreamingChatMessage extends ChatMessage {
  isStreaming?: boolean
  thinkingStatus?: ThinkingStatus
}

export interface ThinkingStatus {
  status: string
  message: string
}

export type StreamChunkType =
  | 'conversation_id'
  | 'thinking'
  | 'text_delta'
  | 'complete_response'
  | 'done'
  | 'error'

export interface StreamChunk {
  type: StreamChunkType
  conversation_id?: string
  status?: string
  message?: string
  text?: string
}

export interface StreamingCallbacks {
  onConversationId?: (conversationId: string) => void
  onThinking?: (status: ThinkingStatus) => void
  onTextDelta?: (text: string) => void
  onCompleteResponse?: (text: string) => void
  onDone?: () => void
  onError?: (error: string) => void
}
