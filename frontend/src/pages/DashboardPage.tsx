import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Activity, Flame, Heart, Zap,
  Dumbbell, Sprout, Trophy, ArrowRight, Loader2, TrendingUp, ChefHat
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { analyticsService, type DashboardStats } from '@/services/analytics.service'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip
} from 'recharts'

export function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await analyticsService.getDashboardData('DOG')
        setStats(result)
      } catch (error) {
        console.error("Failed to fetch analytics", error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <ChefHat className="h-12 w-12 text-primary/50" />
          <p className="text-lg font-medium text-slate-500">Curating your culinary data...</p>
        </div>
      </div>
    )
  }

  if (!stats) return <div className="flex h-screen items-center justify-center">No Data Available</div>

  // --- DATA PREPARATION ---
  const conversionData = [
    { name: 'Transformed', value: stats.total_transformations },
    { name: 'Standard Search', value: stats.total_searches - stats.total_transformations },
  ]
  const PIE_COLORS = ['#10b981', '#f1f5f9']

  const ingredientsData = stats.top_ingredients.slice(0, 6).map(i => ({
    name: i.name.length > 12 ? i.name.substring(0, 12) + '...' : i.name,
    full_name: i.name,
    count: i.count
  }));

  return (
    <div className="min-h-screen bg-slate-50/50 p-6 md:p-8 font-sans text-slate-900">

      {/* --- HEADER --- */}
      <div className="mx-auto max-w-7xl mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <Activity className="h-8 w-8 text-primary" />
            Your Nutrition Hub
          </h1>
          <p className="text-slate-500 mt-1">Real-time tracking of your culinary transformations and health impact.</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/')} className="gap-2 border-slate-200 hover:bg-white hover:text-primary transition-colors shadow-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Kitchen
        </Button>
      </div>

      <div className="mx-auto max-w-7xl space-y-6">

        {/* =================================================================================
            SECTION 1: HERO METRICS (THE "IMPACT" ROW)
            Style: Coloured cards with gradients to emphasize positive outcome
           ================================================================================= */}
        <div className="grid gap-4 md:grid-cols-3">

          {/* HEALTH SCORE */}
          <Card className="relative overflow-hidden border-emerald-100 bg-gradient-to-br from-white to-emerald-50/50 shadow-sm hover:shadow-md transition-shadow">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <Heart className="h-24 w-24 text-emerald-600" />
            </div>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-emerald-600 uppercase tracking-wider flex items-center gap-2">
                <Heart className="h-4 w-4" /> Avg. Health Boost
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-emerald-900">+{stats.avg_health_score_gain}</span>
                <span className="text-sm font-medium text-emerald-600">points</span>
              </div>
              <p className="text-xs text-emerald-800/60 mt-2">Improvement per recipe transformed</p>
            </CardContent>
          </Card>

          {/* CALORIES */}
          <Card className="relative overflow-hidden border-orange-100 bg-gradient-to-br from-white to-orange-50/50 shadow-sm hover:shadow-md transition-shadow">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <Flame className="h-24 w-24 text-orange-600" />
            </div>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-orange-600 uppercase tracking-wider flex items-center gap-2">
                <Flame className="h-4 w-4" /> Calories Cut
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-orange-900">{stats.total_calories_saved}</span>
                <span className="text-sm font-medium text-orange-600">kcal</span>
              </div>
              <p className="text-xs text-orange-800/60 mt-2">Total energy saved via smart swaps</p>
            </CardContent>
          </Card>

          {/* PROTEIN */}
          <Card className="relative overflow-hidden border-blue-100 bg-gradient-to-br from-white to-blue-50/50 shadow-sm hover:shadow-md transition-shadow">
            <div className="absolute top-0 right-0 p-4 opacity-10">
                <Dumbbell className="h-24 w-24 text-blue-600" />
            </div>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-blue-600 uppercase tracking-wider flex items-center gap-2">
                <Dumbbell className="h-4 w-4" /> Protein Gained
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-blue-900">+{stats.total_protein_gained}</span>
                <span className="text-sm font-medium text-blue-600">grams</span>
              </div>
              <p className="text-xs text-blue-800/60 mt-2">Muscle-building macro added</p>
            </CardContent>
          </Card>
        </div>

        {/* =================================================================================
            SECTION 2: DEEP DIVE (THE "GRID" ROW)
            Layout: 8 columns for ingredients (Left), 4 columns for Activity (Right)
           ================================================================================= */}
        <div className="grid gap-6 md:grid-cols-12">

          {/* LEFT: INGREDIENTS CHART */}
          <Card className="md:col-span-8 shadow-sm border-slate-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-lg font-bold text-slate-800">Flavor Profile</CardTitle>
                <CardDescription>Top ingredients appearing in your searches</CardDescription>
              </div>
              <Badge variant="secondary" className="gap-1 bg-slate-100 text-slate-600 hover:bg-slate-200">
                <Sprout className="h-3 w-3" />
                {stats.ingredient_diversity_index} unique items
              </Badge>
            </CardHeader>
            <CardContent className="h-[320px] pl-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ingredientsData} layout="vertical" margin={{ left: 10, right: 30, top: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#e2e8f0" />
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="name"
                    type="category"
                    width={100}
                    tick={{fontSize: 12, fill: '#64748b'}}
                    axisLine={false}
                    tickLine={false}
                  />
                  <RechartsTooltip
                     cursor={{fill: '#f8fafc'}}
                     contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                     labelFormatter={(label) => {
                        const original = ingredientsData.find(i => i.name === label);
                        return original ? original.full_name : label;
                     }}
                  />
                  <Bar
                    dataKey="count"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                    barSize={20}
                    name="Frequency"
                  >
                     {ingredientsData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#2563eb' : '#60a5fa'} />
                     ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* RIGHT: ACTIVITY & CONVERSION */}
          <div className="md:col-span-4 flex flex-col gap-4">

            {/* Conversion Card */}
            <Card className="flex-1 shadow-sm border-slate-200 flex flex-col">
              <CardHeader className="pb-0">
                <CardTitle className="text-lg font-bold text-slate-800">Activity Ratio</CardTitle>
                <CardDescription>Search vs. Transform</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col items-center justify-center min-h-[200px]">
                <div className="h-[160px] w-full relative">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={conversionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={70}
                        paddingAngle={4}
                        dataKey="value"
                        startAngle={90}
                        endAngle={-270}
                      >
                        {conversionData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center Text */}
                  <div className="absolute inset-0 flex items-center justify-center flex-col pointer-events-none">
                     <span className="text-2xl font-bold text-slate-800">{stats.conversion_rate}%</span>
                     <span className="text-[10px] text-slate-400 uppercase font-semibold">Action Rate</span>
                  </div>
                </div>
                <div className="flex w-full justify-between px-4 mt-2 text-xs text-slate-500">
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div> Transformed
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-slate-200"></div> Browsing
                    </div>
                </div>
              </CardContent>
            </Card>

            {/* Total Volume Mini-Card */}
            <Card className="shadow-sm bg-slate-800 text-white border-none">
                <CardContent className="p-4 flex items-center justify-between">
                    <div>
                        <p className="text-slate-400 text-xs uppercase font-bold tracking-wider">Total Interactions</p>
                        <p className="text-2xl font-bold">{stats.total_searches}</p>
                    </div>
                    <div className="h-10 w-10 rounded-full bg-slate-700 flex items-center justify-center">
                        <Zap className="h-5 w-5 text-amber-400" />
                    </div>
                </CardContent>
            </Card>

          </div>
        </div>

        {/* =================================================================================
            SECTION 3: HIGHLIGHTS (THE "TROPHY" ROW)
            Layout: 8 columns for Biggest Win (Left), 4 columns for Top Diet (Right)
           ================================================================================= */}
        <div className="grid gap-6 md:grid-cols-12">

            {/* BIGGEST WIN */}
            <Card className="md:col-span-8 bg-gradient-to-r from-amber-50 via-white to-white border-amber-200 shadow-sm relative overflow-hidden">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-amber-800">
                        <Trophy className="h-5 w-5 fill-amber-500 text-amber-600" />
                        Biggest Optimization Record
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {stats.biggest_optimization ? (
                        <div className="flex flex-col md:flex-row items-center gap-6">
                            <div className="flex-1 space-y-4 w-full">
                                <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-amber-100 shadow-sm">
                                    <span className="text-slate-500 line-through text-sm">{stats.biggest_optimization.original_name}</span>
                                    <ArrowRight className="h-4 w-4 text-amber-400" />
                                    <span className="text-slate-900 font-semibold">{stats.biggest_optimization.transformed_name}</span>
                                </div>
                            </div>
                            <div className="flex flex-col items-center justify-center min-w-[120px]">
                                <span className="text-3xl font-extrabold text-amber-600">+{stats.biggest_optimization.health_score_delta}</span>
                                <span className="text-xs font-bold text-amber-800/60 uppercase">Health Points</span>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-4 text-slate-400 text-sm">No transformations recorded yet.</div>
                    )}
                </CardContent>
            </Card>

            {/* TOP CONSTRAINT / FUN STAT */}
            <Card className="md:col-span-4 bg-indigo-50/50 border-indigo-100 shadow-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-indigo-700 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Top Preference
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="py-2">
                        <div className="text-xl font-bold text-slate-900 truncate" title={stats.top_diet_constraint}>
                            {stats.top_diet_constraint || "None"}
                        </div>
                        <p className="text-xs text-slate-500 mt-1">This is your most frequent dietary filter.</p>
                    </div>
                </CardContent>
            </Card>

        </div>

      </div>
    </div>
  )
}
