import { PlusCircle, MessageSquare, LogOut, User, ChevronDown , Loader2 } from 'lucide-react'
// import { useNavigate, useLocation } from 'react-router-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  // DropdownMenuLabel,
  // DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useState, useEffect } from 'react'
import chatService from '@/services/chat.service'
import { cn } from '@/lib/utils'

export function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  // const location = useLocation();
  // Get the account name we saved earlier during the OAuth flow
  const accountName = localStorage.getItem('snowflake_account_display') || 'Snowflake User'
  const [conversations, setConversations] = useState<{id: string, title: string}[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);


  useEffect(() => {
  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const history = await chatService.getConversations();
      setConversations(history);
    } catch (e) {
      console.error("Failed to load sidebar history", e);
    } finally {
      setIsHistoryLoading(false);
    }
  };
  fetchHistory();
}, [location.pathname]); // Re-fetch when URL changes (so new chats appear)

  const createNewChat = async () => {
    navigate(`/chat/`);
  };

  const handleLogout = async () => {
      localStorage.clear();
      window.location.href = '/';
  };

return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* SIDEBAR */}
      <aside className="hidden md:flex w-64 flex-col border-r bg-muted/20">
        <div className="p-4">
          <Button 
            onClick={createNewChat} 
            className="w-full justify-start gap-2 shadow-sm" 
            variant="default"
          >
            <PlusCircle className="h-4 w-4" />
            New Recipe Chat
          </Button>
        </div>
        
        <ScrollArea className="flex-1 px-3 pb-4">
          <div className="space-y-1">
            <p className="px-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              History
            </p>

            {/* LOADING STATE: Skeleton items */}
            {isHistoryLoading ? (
              <div className="space-y-3 px-2 mt-2">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div 
                    key={i} 
                    className="flex items-center gap-3 py-2 px-2 rounded-md animate-pulse"
                    style={{ animationDelay: `${i * 100}ms` }} // Staggered effect
                  >
                    {/* The Icon Placeholder */}
                    <div className="h-4 w-4 rounded bg-foreground/20 shrink-0" /> 
                    
                    {/* The Text Placeholder - Darker and varying widths */}
                    <div className={cn(
                      "h-3.5 rounded bg-foreground/15",
                      i % 3 === 0 ? "w-24" : i % 2 === 0 ? "w-32" : "w-28"
                    )} />
                  </div>
                ))}
              </div>
            ) : (
              /* ACTUAL DATA */
              conversations.map((chat) => (
                <Button 
                  key={chat.id} 
                  variant={location.pathname === `/chat/${chat.id}` ? "secondary" : "ghost"}
                  className="w-full justify-start font-normal truncate group"
                  onClick={() => navigate(`/chat/${chat.id}`)}
                >
                  <MessageSquare className="mr-2 h-4 w-4 opacity-70 group-hover:opacity-100" />
                  {chat.title}
                </Button>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b px-6 bg-card">
          <div className="font-bold text-primary flex items-center gap-2">
            <span className="md:hidden italic">NR</span>
            <span className="hidden md:inline">NutriRAG Assistant</span>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2 px-2">
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="bg-primary/10 text-primary text-[10px]">
                    {accountName.substring(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{accountName}</span>
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={handleLogout} className="text-destructive font-medium">
                <LogOut className="mr-2 h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 overflow-hidden relative bg-background">
          {children}
        </main>
      </div>
    </div>
  )
}