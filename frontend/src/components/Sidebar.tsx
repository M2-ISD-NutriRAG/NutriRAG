import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, LayoutDashboard, UtensilsCrossed } from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  {
    name: 'Conversation',
    href: '/',
    icon: MessageSquare,
  },
  {
    name: 'Tableau de bord',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="flex h-screen w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <UtensilsCrossed className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-foreground">NutriRAG</h1>
          <p className="text-xs text-muted-foreground">Assistant IA Recettes</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        <p className="text-xs text-muted-foreground text-center">
          Master ISD - Paris-Saclay
          <br />
          Data & IA Project 2025-2026
        </p>
      </div>
    </div>
  )
}

