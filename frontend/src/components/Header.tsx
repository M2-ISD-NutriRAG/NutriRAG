import { useLocation } from 'react-router-dom'

const pageTitles: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'Chat IA',
    description: 'Discutez avec NutriRAG pour trouver et transformer des recettes',
  },
  '/dashboard': {
    title: 'Tableau de bord',
    description: 'Analyses et statistiques',
  },
}

export function Header() {
  const location = useLocation()
  const pageInfo = pageTitles[location.pathname] || {
    title: 'NutriRAG',
    description: 'Assistant IA Recettes',
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

