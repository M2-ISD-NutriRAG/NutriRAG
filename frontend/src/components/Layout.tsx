import { User, LogOut, ChevronDown } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'

import { Button } from '@/components/ui/button'

export function Layout({ children }: { children: React.ReactNode }) {
  // Get the account name we saved earlier during the OAuth flow
  const accountName = localStorage.getItem('snowflake_account_display') || 'Snowflake User'

  const handleLogout = async () => {
    // 1. Clear Snowflake tokens
      localStorage.removeItem('snowflake_token');
      localStorage.removeItem('snowflake_refresh_token');
      
      // 2. Clear UI-related data
      localStorage.removeItem('snowflake_account_display');
      localStorage.removeItem('pending_snowflake_account');

      // 3. Force a reload or redirect to the home page
      // This triggers your App.tsx logic to see there's no token and show AuthPage
      window.location.href = '/';
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      {/* Header */}
      <header className="flex h-16 items-center justify-between border-b px-6">
        <div className="flex items-center gap-2 font-bold">
          <div className="rounded bg-primary p-1 text-primary-foreground">
             {/* Your Logo Icon */}
             NR
          </div>
          <span>NutriRAG</span>
        </div>

        {/* Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2 focus-visible:ring-0">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary/10 text-primary">
                  {accountName.substring(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col items-start text-sm">
                <span className="font-medium leading-none">{accountName}</span>
                <span className="text-xs text-muted-foreground italic">Connected</span>
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-muted-foreground cursor-default">
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={handleLogout}
              className="text-destructive focus:bg-destructive focus:text-destructive-foreground cursor-pointer"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      {/* Page Content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}