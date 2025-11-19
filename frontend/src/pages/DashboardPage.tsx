import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, Users, TrendingUp, Clock } from 'lucide-react'

export function DashboardPage() {
  // Données fictives pour démonstration
  const kpis = [
    {
      title: 'Recherches totales',
      value: '1,234',
      change: '+12.5%',
      icon: Activity,
      color: 'text-blue-500',
    },
    {
      title: 'Transformations de recettes',
      value: '456',
      change: '+8.2%',
      icon: TrendingUp,
      color: 'text-green-500',
    },
    {
      title: 'Utilisateurs actifs',
      value: '89',
      change: '+23.1%',
      icon: Users,
      color: 'text-purple-500',
    },
    {
      title: 'Temps de réponse moyen',
      value: '1.2s',
      change: '-5.3%',
      icon: Clock,
      color: 'text-orange-500',
    },
  ]

  return (
    <div className="p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {kpis.map((kpi, index) => (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {kpi.title}
                </CardTitle>
                <kpi.icon className={cn('h-4 w-4', kpi.color)} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{kpi.value}</div>
                <p className="text-xs text-muted-foreground">
                  <span className={kpi.change.startsWith('+') ? 'text-green-500' : 'text-red-500'}>
                    {kpi.change}
                  </span>
                  {' '}par rapport à la semaine dernière
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Area */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          {/* Graphique d'aperçu */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Vue d'ensemble</CardTitle>
              <CardDescription>
                Analyses et statistiques d'utilisation
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <Activity className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>La visualisation graphique sera affichée ici</p>
                <p className="text-sm mt-2">Connectez-vous au service d'analyse pour voir les données réelles</p>
              </div>
            </CardContent>
          </Card>

          {/* Activité récente */}
          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Activité récente</CardTitle>
              <CardDescription>
                Dernières interactions des utilisateurs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[1, 2, 3, 4].map((item) => (
                  <div key={item} className="flex items-center gap-4">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">Activité {item}</p>
                      <p className="text-xs text-muted-foreground">
                        Il y a {item} minute{item > 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Informations supplémentaires */}
        <Card>
          <CardHeader>
            <CardTitle>Recettes populaires</CardTitle>
            <CardDescription>
              Recettes les plus recherchées et transformées
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center text-muted-foreground py-8">
              <TrendingUp className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>Les recettes populaires seront affichées ici</p>
              <p className="text-sm mt-2">Les données seront chargées depuis le service d'analyse</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Add cn utility import at top
import { cn } from '@/lib/utils'

