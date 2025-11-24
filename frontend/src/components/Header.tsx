import { useLocation } from 'react-router-dom'

const pageTitles: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'AI Chat',
    description: 'Chat with NutriRAG to find and transform recipes',
  },
  '/dashboard': {
    title: 'Dashboard',
    description: 'Analytics and statistics',
  },
}

export function Header() {
  const location = useLocation()
  const pageInfo = pageTitles[location.pathname] || {
    title: 'NutriRAG',
    description: 'AI Recipe Assistant',
  }

  return (
    <div className="border-b bg-card">
      <div className="flex h-16 items-center px-8">
        <div>
          <h2 className="text-2xl font-bold text-foreground">{pageInfo.title}</h2>
          <p className="text-sm text-muted-foreground">{pageInfo.description}</p>
        </div>
      </div>
    </div>
  )
}

