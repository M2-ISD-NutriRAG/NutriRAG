import { MessageSquare, LogOut, ChevronDown , Trash2, Plus } from 'lucide-react'
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
import { cn, getAvatarColor, getInitials } from '@/lib/utils'

export function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const accountName = localStorage.getItem('snowflake_account_display') || 'Snowflake User'
  
  const [conversations, setConversations] = useState<{id: string, title: string}[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [newlyAddedId, setNewlyAddedId] = useState<string | null>(null);


  useEffect(() => {
  const fetchHistory = async () => {
    const isInitialLoad = conversations.length === 0;
    if (isInitialLoad) setIsHistoryLoading(true);

    try {
      const history = await chatService.getConversations();

      // HIGHLIGHT LOGIC:
      if (conversations.length > 0 && history.length > conversations.length) {
        const newItems = history.filter((h: { id: string }) => !conversations.find(c => c.id === h.id));
        if (newItems.length > 0) {
          setNewlyAddedId(newItems[0].id);
          setTimeout(() => setNewlyAddedId(null), 1000); // Remove highlight after 3s
        }
      }

      if (JSON.stringify(history) !== JSON.stringify(conversations))
          setConversations(history);
    } catch (e) {
      console.error("Failed to load sidebar history", e);
    } finally {
      setIsHistoryLoading(false);
    }
  };
  fetchHistory();
}, [location.pathname]); // Re-fetch when URL changes (so new chats appear)


const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent navigating to the chat when clicking delete
    try {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      await chatService.deleteConversation(id);
      // if (location.pathname === `/chat/${id}`) navigate('/chat/'); // Removed navigation on delete to avoid lag...
    } catch (error) {
      console.error("Failed to delete", error);
    }
  };

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
            onClick={() => createNewChat()} 
            variant="outline"
            className="w-full justify-start gap-2 border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all group rounded-xl py-6"
          >
            <Plus className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
            <span className="font-semibold text-sm">New recipe chat</span>
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
              <>
                {/* Inside ScrollArea mapping */}
                {conversations.map((chat) => (
              <div key={chat.id} className="relative group px-1">
                <Button 
                  variant={location.pathname === `/chat/${chat.id}` ? "secondary" : "ghost"}
                  className={cn(
                    "w-full justify-start font-normal truncate pr-8 transition-all duration-500",
                    // The Highlight Animation
                    newlyAddedId === chat.id 
                      ? "bg-primary/20 ring-1 ring-primary/50 text-primary" 
                      : ""
                  )}
                  onClick={() => navigate(`/chat/${chat.id}`)}
                >
                  <MessageSquare className="mr-2 h-4 w-4 shrink-0 opacity-70" />
                  <span className="truncate">{chat.title || "New Conversation"}</span>
                </Button>

                {/* Delete Icon - Visible only on Hover */}
                <button
                  onClick={(e) => handleDelete(e, chat.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md 
                            opacity-0 group-hover:opacity-100 hover:bg-destructive/10 
                            hover:text-destructive transition-all text-muted-foreground"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
              </>
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
                  <AvatarFallback style={{ backgroundColor: getAvatarColor(accountName) }} className="bg-primary/10 text-white text-[10px]">
                    {getInitials(accountName)}
                  </AvatarFallback>
                </Avatar>
                {/* To change color of avatar use getAvatarColor from utils in this way: 
                <AvatarFallback style={{ backgroundColor: getAvatarColor(accountName) }} className="text-white text-[10px]">
                  {getInitials(accountName)}
                </AvatarFallback>
                */}
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