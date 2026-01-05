import { PlusCircle, MessageSquare, LogOut, User, ChevronDown } from 'lucide-react'
// import { useNavigate, useLocation } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
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

export function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  // const location = useLocation();
  // Get the account name we saved earlier during the OAuth flow
  const accountName = localStorage.getItem('snowflake_account_display') || 'Snowflake User'
  const [conversations, setConversations] = useState<{id: string, title: string}[]>([]);

  useEffect(() => {
    // TODO: Replace with actual API call to fetch conversations
    const mockHistory = [
      {id: '1', title: 'Heavy Chicken Pasta'},
      {id: '2', title: 'Vegan Salad Ideas'},
    ];
  setConversations(mockHistory);
  }, []);

  const createNewChat = async () => {
    // 1. TODO: Call backend to create a new row in Snowflake CONVERSATIONS table
    // 2. TODO: Get the new ID back
    const newId = crypto.randomUUID(); // Temporary; get this from backend later
    
    // 3. Navigate to the new chat page
    navigate(`/chat/${newId}`);
  };

  const handleLogout = async () => {
    // 1. Clear Snowflake tokens
      localStorage.clear();

      // 3. Force a reload or redirect to the home page
      // This triggers your App.tsx logic to see there's no token and show AuthPage
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
            {conversations.map((chat) => (
              <Button 
                key={chat.id} 
                variant={location.pathname === `/chat/${chat.id}` ? "secondary" : "ghost"}
                className="w-full justify-start font-normal truncate group"
                onClick={() => navigate(`/chat/${chat.id}`)}
              >
                <MessageSquare className="mr-2 h-4 w-4 opacity-70 group-hover:opacity-100" />
                {chat.title}
              </Button>
            ))}
          </div>
        </ScrollArea>
      </aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* HEADER */}
        <header className="flex h-14 items-center justify-between border-b px-6 bg-card">
          <div className="font-bold text-primary flex items-center gap-2">
            <span className="md:hidden italic">NR</span> {/* Logo for mobile */}
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
              <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* CHAT PAGE RENDERS HERE */}
        <main className="flex-1 overflow-hidden relative">
          {children}
        </main>
      </div>
    </div>
  )
}