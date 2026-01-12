import { useState, useRef, useEffect } from 'react'
import {
  Send, Loader2, Sparkles, LayoutDashboard, PieChart as PieChartIcon,
  ArrowRight, Activity, Flame, Dumbbell, Scale
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MarkdownMessage } from '@/components/MarkdownMessage'
import { Badge } from '@/components/ui/badge'
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger
} from "@/components/ui/sheet"
import { cn } from '@/lib/utils'

// Services
import { chatService, type ChatMessage, type ThinkingStatus } from '@/services/chat.service'
import { analyticsService, type ConversationStats } from '@/services/analytics.service'

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
  const [thinkingHistory, setThinkingHistory] = useState<ThinkingStatus[]>([]) // Store thinking messages for current response
  const scrollRef = useRef<HTMLDivElement>(null)

  // --- STATE STATS SESSION ---
  const [stats, setStats] = useState<ConversationStats | null>(null)
  const [isStatsLoading, setIsStatsLoading] = useState(false)

  // --- ROUTING ---
  const { id } = useParams();
  const navigate = useNavigate();

  // Create a ref to track which ID the current messages belong to
  const loadedIdRef = useRef<string | undefined>(undefined);

  // EFFECT: Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isThinking, streamingContent, thinkingStatus, thinkingHistory])

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

  // --- HANDLERS ---

  // Charger les stats de la session
  const handleOpenStats = async () => {
    if (!id) return;
    setIsStatsLoading(true);
    try {
      const data = await analyticsService.getConversationStats(id);
      setStats(data);
    } catch (error) {
      console.error("Failed to load stats", error);
    } finally {
      setIsStatsLoading(false);
    }
  };

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
    setThinkingHistory([]); // Clear previous thinking history

    // Use a ref to track accumulated content for proper onDone handling
    let accumulatedContent = '';

    try {
      console.log('Starting streaming message...', { messageContent, conversationId: id });

      await chatService.sendMessageStream(
        {
          message: userMessage.content,
          conversation_history: messages,
          conversation_id: id || undefined,
        },
        {
          onConversationId: (conversationId) => {
            console.log('Received conversation ID:', conversationId);
            if (!id) {
              loadedIdRef.current = conversationId;
              navigate(`/chat/${conversationId}`, { replace: true });
            }
          },
          onThinking: (status) => {
            console.log('Thinking status:', status);
            setThinkingStatus(status);
            setThinkingHistory(prev => [...prev, status]); // Add to thinking history
          },
          onTextDelta: (text) => {
            console.log('Text delta:', text);
            accumulatedContent += text;
            setStreamingContent(accumulatedContent);
          },
          onCompleteResponse: (text) => {
            console.log('Complete response:', text);
            // Fallback for complete response if deltas weren't received
            if (!accumulatedContent) {
              accumulatedContent = text;
              setStreamingContent(text);
            }
          },
          onDone: () => {
            console.log('Stream completed. Final content:', accumulatedContent);
            // Add final message to messages array using accumulated content
            const assistantMessage: ChatMessage = {
              id: crypto.randomUUID(),
              role: 'assistant',
              content: accumulatedContent || 'No response received',
              timestamp: new Date().toISOString(),
              thinkingHistory: thinkingHistory.length > 0 ? [...thinkingHistory] : undefined
            };

            setMessages((prev) => [...prev, assistantMessage]);
            setIsThinking(false);
            setStreamingContent('');
            setThinkingStatus(null);
            setThinkingHistory([]); // Clear thinking history after saving
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
    <div className="flex h-full flex-col bg-background relative">

      {/* --- HEADER BUTTONS --- */}
      <div className="absolute top-6 left-6 z-20 flex gap-3">

        {/* 2. Current Session Stats Sheet */}
        {id && (
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                className="shadow-md border bg-emerald-50/95 border-emerald-200 text-emerald-700 backdrop-blur-sm hover:bg-emerald-100 h-10 px-4 text-sm font-medium transition-all hover:scale-105"
                onClick={handleOpenStats}
              >
                <PieChartIcon className="mr-2 h-4 w-4" />
                Conversation Insights
              </Button>
            </SheetTrigger>

            {/* --- SHEET CONTENT (STATS PANEL) --- */}
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto bg-slate-50/80 backdrop-blur-sm p-0">
              <div className="p-6 bg-white border-b sticky top-0 z-10">
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2 text-xl font-bold text-slate-900">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Activity className="h-5 w-5 text-primary"/>
                      </div>
                      Conversation Insights
                  </SheetTitle>
                  <SheetDescription>
                    Real-time impact of your {stats?.total_messages || 0} searchs.
                  </SheetDescription>
                </SheetHeader>
              </div>

              {isStatsLoading ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <Loader2 className="h-10 w-10 animate-spin text-primary/50"/>
                    <p className="text-sm text-muted-foreground">Analyzing culinary data...</p>
                  </div>
              ) : stats ? (
                  (() => {
                    const totalCaloriesDelta = stats.transformations_list.reduce((acc, t) => acc + t.delta_calories, 0);
                    const totalProteinDelta = stats.transformations_list.reduce((acc, t) => acc + t.delta_protein, 0);

                    const isCalCut = totalCaloriesDelta <= 0;

                    return (
                      <div className="p-6 space-y-8">

                          {/* SECTION 1: TOTAL IMPACT (HERO CARDS) */}
                          <div className="grid grid-cols-2 gap-4">
                              {/* Calories Card */}
                              <div className="relative overflow-hidden bg-gradient-to-br from-orange-50 to-white p-4 rounded-2xl border border-orange-100 shadow-sm">
                                  <div className="absolute top-0 right-0 p-3 opacity-10">
                                      <Flame className="h-16 w-16 text-orange-500"/>
                                  </div>
                                  <div className="flex flex-col relative z-10">
                                      <span className="text-[10px] font-bold uppercase tracking-wider text-orange-600/70 flex items-center gap-1 mb-1">
                                        <Flame className="h-3 w-3"/> {isCalCut ? "Total Cut" : "Total Added"}
                                      </span>
                                      <span className="text-3xl font-extrabold text-slate-800">
                                        {/* On affiche la valeur absolue pour le chiffre principal */}
                                        {Math.abs(totalCaloriesDelta).toFixed(0)}
                                      </span>
                                      <span className="text-xs font-medium text-slate-500">kcal {isCalCut ? "removed" : "added"}</span>
                                  </div>
                              </div>

                              {/* Protein Card */}
                              <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 to-white p-4 rounded-2xl border border-blue-100 shadow-sm">
                                  <div className="absolute top-0 right-0 p-3 opacity-10">
                                      <Dumbbell className="h-16 w-16 text-blue-500"/>
                                  </div>
                                  <div className="flex flex-col relative z-10">
                                      <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600/70 flex items-center gap-1 mb-1">
                                        <Dumbbell className="h-3 w-3"/> Net Change
                                      </span>
                                      <span className="text-3xl font-extrabold text-slate-800">
                                        {totalProteinDelta > 0 ? '+' : ''}{totalProteinDelta.toFixed(1)}
                                      </span>
                                      <span className="text-xs font-medium text-slate-500">g protein</span>
                                  </div>
                              </div>
                          </div>

                          {/* SECTION 2: TRANSFORMATIONS LIST */}
                          <div className="space-y-4">
                              <div className="flex items-center justify-between">
                                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                                  <Scale className="h-4 w-4 text-slate-500"/>
                                  Transformations ({stats.transformations_list.length})
                                </h3>
                                <div className="h-px flex-1 bg-slate-200 ml-4"></div>
                              </div>

                              {stats.transformations_list.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 px-4 text-center border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
                                    <Sparkles className="h-8 w-8 text-slate-300 mb-2" />
                                    <p className="text-sm font-medium text-slate-600">No recipes transformed yet.</p>
                                    <p className="text-xs text-slate-400">Ask me to modify a recipe to see stats here.</p>
                                </div>
                              ) : (
                                stats.transformations_list.map((t, idx) => (
                                  <Card key={idx} className="overflow-hidden border-slate-200 shadow-sm hover:shadow-md transition-all duration-300 group">
                                      {/* Card Header */}
                                      <div className="p-4 bg-white border-b border-slate-100">
                                          <div className="flex justify-between items-start gap-4">
                                              <div>
                                                  <h4 className="font-bold text-slate-800 text-base leading-tight group-hover:text-primary transition-colors">
                                                    {t.transformed_name}
                                                  </h4>
                                                  <div className="flex items-center gap-1.5 mt-1.5 text-xs text-slate-500">
                                                      <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">From</span>
                                                      <span className="line-through opacity-70 truncate max-w-[150px]">{t.original_name}</span>
                                                  </div>
                                              </div>
                                              <Badge
                                                variant="secondary"
                                                className={cn(
                                                  "whitespace-nowrap font-bold shadow-sm",
                                                  t.delta_health_score > 0
                                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                                    : "bg-slate-100 text-slate-600"
                                                )}
                                              >
                                                  {t.delta_health_score > 0 ? '+' : ''}{t.delta_health_score} Score
                                              </Badge>
                                          </div>
                                      </div>

                                      {/* Nutrients Grid (Tiles) */}
                                      <div className="p-3 bg-slate-50/30 grid grid-cols-3 gap-2">
                                          <DeltaTile label="Calories" value={t.delta_calories} unit="kcal" inverse={true} />
                                          <DeltaTile label="Protein" value={t.delta_protein} unit="g" inverse={false} />
                                          <DeltaTile label="Carbs" value={t.delta_carbs} unit="g" inverse={true} />

                                          <div className="col-span-3 h-px bg-slate-100 my-1"/>

                                          <DeltaTile label="Fat" value={t.delta_fat} unit="g" inverse={true} />
                                          <DeltaTile label="Sugar" value={t.delta_sugar} unit="g" inverse={true} />
                                          <DeltaTile label="Fiber" value={t.delta_fiber} unit="g" inverse={false} />
                                      </div>
                                  </Card>
                                ))
                              )}
                          </div>
                      </div>
                    );
                  })()
              ) : null}
            </SheetContent>
          </Sheet>
        )}
      </div>

      {/* Messages Area */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4 pt-20 relative">
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

                {message.role === 'user' ? (
                  <div
                    className="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm border bg-primary text-primary-foreground border-primary"
                  >
                    <MarkdownMessage content={message.content} isUserMessage={true} />
                  </div>
                ) : (
                  <div className="max-w-[85%] space-y-2">
                    {/* Show thinking history above assistant messages */}
                    {message.thinkingHistory && message.thinkingHistory.length > 0 && (
                      <div className="space-y-1">
                        {message.thinkingHistory.map((thinking, thinkingIndex) => (
                          <div key={thinkingIndex} className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs">
                            <div className="flex items-center gap-2 text-amber-700">
                              <div className="flex gap-1">
                                <span className="w-1 h-1 bg-amber-400 rounded-full"></span>
                                <span className="w-1 h-1 bg-amber-400 rounded-full"></span>
                                <span className="w-1 h-1 bg-amber-400 rounded-full"></span>
                              </div>
                              <span className="font-medium capitalize">{thinking.status.replace(/_/g, ' ')}</span>
                            </div>
                            <p className="text-amber-600 mt-1">{thinking.message}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm border bg-card text-card-foreground border-border">
                      <MarkdownMessage content={message.content} isUserMessage={false} />
                    </div>
                  </div>
                )}
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
                       <MarkdownMessage content={streamingContent} isUserMessage={false} />
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

// --- HELPER COMPONENT (DELTA ROW) ---
function DeltaTile({ label, value, unit, inverse }: { label: string, value: number, unit: string, inverse: boolean }) {
    // On affiche tout, même les zéros, mais en gris clair
    const isZero = Math.abs(value) < 0.1;

    let colorClass = "text-slate-400 bg-white border-slate-100";
    let iconColor = "text-slate-300";

    if (!isZero) {
        const isGood = inverse ? value < 0 : value > 0;
        // Vert pour positif, Ambre/Rouge pour négatif (moins agressif que le rouge pur)
        colorClass = isGood
            ? "text-emerald-700 bg-emerald-50/50 border-emerald-100 shadow-sm"
            : "text-amber-700 bg-amber-50/50 border-amber-100 shadow-sm";
        iconColor = isGood ? "text-emerald-500" : "text-amber-500";
    }

    const sign = value > 0 ? '+' : '';

    return (
        <div className={cn("flex flex-col items-center justify-center p-2 rounded-xl border transition-all", colorClass)}>
            <span className={cn("text-[10px] font-bold uppercase tracking-wider mb-0.5 opacity-70")}>
                {label}
            </span>
            <span className="font-bold text-sm">
                {isZero ? "-" : `${sign}${value}`}
                {!isZero && <span className="text-[10px] font-normal opacity-70 ml-0.5">{unit}</span>}
            </span>
        </div>
    )
}
