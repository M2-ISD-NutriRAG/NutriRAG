import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { chatService, type ChatMessage, type ThinkingStatus } from '@/services/chat.service'
import { cn } from '@/lib/utils'

import { useParams, useNavigate } from 'react-router-dom'

const suggestions = [
  "Find me a healthy vegetarian recipe",
  "Transform this recipe into a low-carb version",
  "What can I make with chicken and rice?",
  "Show me high-protein breakfast ideas",
]

export function ChatPage() {
  // const [messages, setMessages] = useState<ChatMessage[]>([
  //   {
  //     id: crypto.randomUUID(),
  //     role: 'assistant',
  //     content: 'Hello! I am NutriRAG, your AI recipe assistant. I can help you find recipes, transform them according to your dietary needs, and provide nutritional information. What would you like to cook today?',
  //     timestamp: new Date().toISOString(),
  //   },
  // ])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false) // For switching chats, initial load, etc.
  const [isThinking, setIsThinking] = useState(false) // For AI response
  const [streamingContent, setStreamingContent] = useState('') // For streaming message content
  const [thinkingStatus, setThinkingStatus] = useState<ThinkingStatus | null>(null) // For thinking display
  const scrollRef = useRef<HTMLDivElement>(null)

  const { id } = useParams();
  const navigate = useNavigate();

  // Create a ref to track which ID the current messages belong to
  const loadedIdRef = useRef<string | undefined>(undefined);


  // EFFECT: Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isThinking, streamingContent, thinkingStatus])

  // EFFECT: Load conversation history when 'id' changes
  useEffect(() => {
    // GUARD: If we have messages and the last message was from the assistant, no need to re-fetch
    if (id === loadedIdRef.current && messages.length > 0) {
      return;
    }
    const fetchMessages = async () => {
      if (id) {
        // CASE: Existing Chat (ID present in URL)
        setIsLoading(true);
        try {
          const history = await chatService.getConversationMessages(id);
          setMessages(history);
          loadedIdRef.current = id; // Update the loaded ID ref
        } catch (error) {
          console.error('Failed to load conversation history:', error)
        } finally {
          setIsLoading(false);
        }
      } else {
        // CASE: New Chat (No ID in URL)
        // Reset to empty/welcome state for a brand new chat
        setMessages([]);
        loadedIdRef.current = undefined;
      }
    };
    fetchMessages();
  }, [id]); // Triggers every time you click a different sidebar item

const handleSend = async (directMessage?: string) => {
  const messageContent = directMessage || input;

  // Validation: check the extracted content instead of just the 'input' state
  if (!messageContent.trim() || isThinking) return;

  const userMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content: messageContent.trim(),
    timestamp: new Date().toISOString(),
  };

  setMessages((prev) => [...prev, userMessage]);
  setInput(''); // Clear input regardless of how it was sent
  setIsThinking(true);
  setStreamingContent(''); // Reset streaming content
  setThinkingStatus(null); // Reset thinking status

  try {
    await chatService.sendMessageStream(
      {
        message: userMessage.content,
        conversation_history: messages,
        conversation_id: id || undefined,
      },
      {
        onConversationId: (conversationId) => {
          if (!id) {
            loadedIdRef.current = conversationId;
            navigate(`/chat/${conversationId}`, { replace: true });
          }
        },
        onThinking: (status) => {
          setThinkingStatus(status);
        },
        onTextDelta: (text) => {
          setStreamingContent((prev) => prev + text);
        },
        onCompleteResponse: (text) => {
          // Fallback for complete response if deltas weren't received
          if (!streamingContent) {
            setStreamingContent(text);
          }
        },
        onDone: () => {
          // Add final message to messages array
          const assistantMessage: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: streamingContent || 'No response received',
            timestamp: new Date().toISOString(),
          };

          setMessages((prev) => [...prev, assistantMessage]);
          setIsThinking(false);
          setStreamingContent('');
          setThinkingStatus(null);
        },
        onError: (error) => {
          console.error('Streaming error:', error);
          const errorMessage: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Sorry, I encountered an error: ${error}`,
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errorMessage]);
          setIsThinking(false);
          setStreamingContent('');
          setThinkingStatus(null);
        },
      }
    );
  } catch (error) {
    console.error('Error sending message:', error);
    const errorMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, errorMessage]);
    setIsThinking(false);
    setStreamingContent('');
    setThinkingStatus(null);
  }
};

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    handleSend(suggestion); // Pass the text directly to skip the state delay
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary opacity-20" />
          <p className="text-sm text-muted-foreground animate-pulse">Loading conversation...</p>
        </div>
      </div>
    )
  }

return (
    <div className="flex h-full flex-col bg-background">
      {/* Messages Area */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4 relative">
        <div className="mx-auto max-w-3xl h-full">

          {/* EMPTY STATE HERO SECTION */}
          {messages.length === 0 && !isThinking && (
            <div className="flex h-[70vh] flex-col items-center justify-center text-center animate-in fade-in zoom-in duration-500">
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-primary/10 text-primary shadow-inner">
                <Sparkles className="h-10 w-10" />
              </div>
              <h1 className="mb-2 text-4xl font-bold tracking-tight text-foreground/90">
                What are we cooking?
              </h1>
              <p className="max-w-md text-muted-foreground">
                Ask NutriRAG to find recipes, calculate macros, or transform your favorite meals into healthy alternatives.
              </p>
            </div>
          )}

          {/* CHAT BUBBLES */}
          <div className="space-y-6">
            {messages.map((message, index) => (
              <div
                key={index}
                className={cn(
                  'flex gap-3 animate-slide-in',
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white shadow-md">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                  </div>
                )}

                <div
                  className={cn(
                    'max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm border',
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-card text-card-foreground border-border'
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))}

            {/* THINKING STATUS & STREAMING CONTENT */}
            {isThinking && (
              <div className="flex gap-3 justify-start animate-in fade-in duration-300">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white shadow-md">
                  <Sparkles className="h-4 w-4 text-amber-400" />
                </div>

                <div className="max-w-[85%] space-y-3">
                  {/* Thinking Status Display */}
                  {thinkingStatus && (
                    <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm">
                      <div className="flex items-center gap-2 text-amber-700">
                        <div className="flex gap-1">
                          <span className="w-1 h-1 bg-amber-400 rounded-full animate-pulse"></span>
                          <span className="w-1 h-1 bg-amber-400 rounded-full animate-pulse [animation-delay:0.2s]"></span>
                          <span className="w-1 h-1 bg-amber-400 rounded-full animate-pulse [animation-delay:0.4s]"></span>
                        </div>
                        <span className="font-medium capitalize">{thinkingStatus.status.replace(/_/g, ' ')}</span>
                      </div>
                      <p className="text-amber-600 mt-1">{thinkingStatus.message}</p>
                    </div>
                  )}

                  {/* Streaming Content Display */}
                  {streamingContent && (
                    <div className="rounded-2xl bg-card text-card-foreground border-border border px-4 py-3 text-sm leading-relaxed shadow-sm">
                      <p className="whitespace-pre-wrap">{streamingContent}</p>
                      <span className="inline-block w-2 h-5 bg-primary animate-pulse ml-1"></span>
                    </div>
                  )}

                  {/* Default thinking indicator when no specific status */}
                  {!thinkingStatus && !streamingContent && (
                    <div className="rounded-2xl bg-muted/40 border px-5 py-4 flex gap-1.5 items-center">
                      <span className="w-1.5 h-1.5 bg-foreground/30 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                      <span className="w-1.5 h-1.5 bg-foreground/30 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                      <span className="w-1.5 h-1.5 bg-foreground/30 rounded-full animate-bounce"></span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Suggestions Overlay (Fixed position above input when empty) */}
      {messages.length === 0 && (
        <div className="px-4 py-2 animate-in slide-in-from-bottom-4 duration-700">
          <div className="mx-auto max-w-3xl flex flex-wrap justify-center gap-2">
            {suggestions.map((suggestion, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleSuggestionClick(suggestion)} // Now triggers auto-send
                className="text-xs rounded-full border-primary/20 hover:bg-primary/5 hover:border-primary/50 transition-all shadow-sm"
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 bg-background">
        <div className="mx-auto max-w-3xl">
          <Card className="p-2 shadow-xl border-primary/5 ring-1 ring-black/5 bg-card/50 backdrop-blur-sm">
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask NutriRAG..."
                className="min-h-[60px] resize-none border-0 focus-visible:ring-0 bg-transparent"
                disabled={isThinking}
              />
              <Button
                onClick={() => handleSend()}
                disabled={!input.trim() || isThinking}
                size="icon"
                className="h-12 w-12 rounded-xl shrink-0"
              >
                {isThinking ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
