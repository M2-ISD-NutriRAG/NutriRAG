import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Activity, Flame, Heart, Zap, Calendar,
  Dumbbell, Sprout, Trophy, ChefHat, ArrowRight,
  Clock, Timer, ThumbsUp, ThumbsDown, Search, Tag, Filter
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { analyticsService, type DashboardStats, type RecipeRanking } from '@/services/analytics.service'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'
import { cn } from '@/lib/utils'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"

export function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  const [timeRange, setTimeRange] = useState("all")

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const result = await analyticsService.getDashboardData('DOG', timeRange)
        setStats(result)
      } catch (error) {
        console.error("Failed to fetch analytics", error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [timeRange])

  if (loading) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <ChefHat className="h-12 w-12 text-primary/50" />
          <p className="text-lg font-medium text-slate-500">Curating your culinary data...</p>
        </div>
      </div>
    )
  }

  if (!stats) return <div className="flex h-full items-center justify-center">No Data Available</div>

  // --- DATA PREPARATION ---

  // 1. Conversion Data (Pie Chart)
  const conversionData = [
    { name: 'Transformed', value: stats.total_transformations },
    { name: 'Standard Search', value: stats.total_searches - stats.total_transformations },
  ];
  const PIE_COLORS = ['#10b981', '#f1f5f9'];

  // 2. Ingredients Data (Bar Chart)
  const ingredientsData = stats.top_ingredients.slice(0, 6).map(i => ({
    name: i.name.length > 12 ? i.name.substring(0, 12) + '...' : i.name,
    full_name: i.name,
    count: i.count
  }));

  // 3. Nutrition Profile Data (Radar Chart)
  // On crée un dataset normalisé pour visualiser l'équilibre
  const nutritionRadarData = [
    { subject: 'Protein', A: stats.search_nutrition_avg.avg_protein, fullMark: 150 },
    { subject: 'Carbs', A: stats.search_nutrition_avg.avg_carbs, fullMark: 150 },
    { subject: 'Fat', A: stats.search_nutrition_avg.avg_fat, fullMark: 150 },
    { subject: 'Sugar', A: stats.search_nutrition_avg.avg_sugar, fullMark: 100 },
    { subject: 'Fiber', A: stats.search_nutrition_avg.avg_fiber * 2, fullMark: 50 }, // Multiplié pour visibilité
  ];
  const maxVal = Math.max(
    ...nutritionRadarData.map(d => d.A)
  );
  const domainMax = maxVal > 0 ? maxVal * 1.2 : 100;

  return (
    <div className="h-full w-full bg-slate-50/50 font-sans text-slate-900 overflow-hidden">

      {/* ScrollArea gère le défilement de toute la page */}
      <ScrollArea className="h-full w-full">
        <div className="p-6 md:p-8 mx-auto max-w-7xl pb-20">

          {/* --- HEADER --- */}
          <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
                <Activity className="h-8 w-8 text-primary" />
                Your Nutrition Hub
              </h1>
              <p className="text-slate-500 mt-1">Real-time tracking of your culinary transformations and health impact.</p>
            </div>
            <div className="flex items-center gap-3">
                {/* SÉLECTEUR DE PÉRIODE */}
                <Select value={timeRange} onValueChange={setTimeRange}>
                  <SelectTrigger className="w-[160px] bg-white border-slate-200 shadow-sm">
                    <div className="flex items-center gap-2 text-slate-600">
                        <Calendar className="h-4 w-4" />
                        <SelectValue placeholder="Select period" />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                    <SelectItem value="90d">Last 3 Months</SelectItem>
                    <SelectItem value="all">All Time</SelectItem>
                  </SelectContent>
                </Select>

                <Button variant="outline" onClick={() => navigate('/')} className="gap-2 border-slate-200 hover:bg-white hover:text-primary transition-colors shadow-sm">
                  <ArrowLeft className="h-4 w-4" /> Back to Kitchen
                </Button>
            </div>
          </div>

          <div className="space-y-8">

            {/* =================================================================================
                SECTION 1: HERO METRICS (KPIs)
               ================================================================================= */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">

              {/* HEALTH SCORE */}
              <Card className="relative overflow-hidden border-emerald-100 bg-gradient-to-br from-white to-emerald-50/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 p-4 opacity-10"><Heart className="h-20 w-20 text-emerald-600" /></div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-emerald-600 uppercase tracking-wider flex items-center gap-2">
                    <Heart className="h-4 w-4" /> Health Boost
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold text-emerald-900">+{stats.avg_health_score_gain}</span>
                    <span className="text-sm font-medium text-emerald-600">pts</span>
                  </div>
                  <p className="text-xs text-emerald-800/60 mt-1">Avg improvement</p>
                </CardContent>
              </Card>

              {/* CALORIES */}
              <Card className="relative overflow-hidden border-orange-100 bg-gradient-to-br from-white to-orange-50/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 p-4 opacity-10"><Flame className="h-20 w-20 text-orange-600" /></div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-orange-600 uppercase tracking-wider flex items-center gap-2">
                    <Flame className="h-4 w-4" /> Calories Cut
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold text-orange-900">{stats.total_calories_saved}</span>
                    <span className="text-sm font-medium text-orange-600">kcal</span>
                  </div>
                  <p className="text-xs text-orange-800/60 mt-1">Total energy saved</p>
                </CardContent>
              </Card>

              {/* PROTEIN */}
              <Card className="relative overflow-hidden border-blue-100 bg-gradient-to-br from-white to-blue-50/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 p-4 opacity-10"><Dumbbell className="h-20 w-20 text-blue-600" /></div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-blue-600 uppercase tracking-wider flex items-center gap-2">
                    <Dumbbell className="h-4 w-4" /> Protein
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold text-blue-900">+{stats.total_protein_gained}</span>
                    <span className="text-sm font-medium text-blue-600">g</span>
                  </div>
                  <p className="text-xs text-blue-800/60 mt-1">Total gained</p>
                </CardContent>
              </Card>

               {/* TIME SAVED */}
               <Card className="relative overflow-hidden border-purple-100 bg-gradient-to-br from-white to-purple-50/50 shadow-sm hover:shadow-md transition-shadow">
                <div className="absolute top-0 right-0 p-4 opacity-10"><Timer className="h-20 w-20 text-purple-600" /></div>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold text-purple-600 uppercase tracking-wider flex items-center gap-2">
                    <Timer className="h-4 w-4" /> Time Saved
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-1">
                    {stats.avg_time_saved > 0 ? '+' : ''}
                    <span className="text-3xl font-extrabold text-purple-900">{stats.avg_time_saved}</span>
                    <span className="text-sm font-medium text-purple-600">min</span>
                  </div>
                  <p className="text-xs text-purple-800/60 mt-1">Avg per recipe</p>
                </CardContent>
              </Card>
            </div>

            {/* =================================================================================
                SECTION 2 (NOUVEAU): SEARCH TRENDS & PROFILE
               ================================================================================= */}
            <div>
              <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                <Search className="h-5 w-5 text-indigo-500" /> Search Habits & Trends
              </h2>

              <div className="grid gap-6 md:grid-cols-3">

                {/* 1. NUTRITION PROFILE (RADAR CHART) */}
                <Card className="md:col-span-1 shadow-sm border-slate-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-slate-700">Average Macro Profile</CardTitle>
                    <CardDescription>Nutritional balance of recipes you explore</CardDescription>
                  </CardHeader>
                  <CardContent className="h-[250px] flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="70%" data={nutritionRadarData}>
                        <PolarGrid stroke="#e2e8f0" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} />
                        <PolarRadiusAxis angle={30} domain={[0, domainMax]} tick={false} axisLine={false} />
                        <Radar name="You" dataKey="A" stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} />
                        <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}/>
                      </RadarChart>
                    </ResponsiveContainer>
                  </CardContent>
                  <div className="px-6 pb-4 flex justify-between text-xs text-slate-500 border-t pt-3">
                    <span>Avg Cal: <strong>{stats.search_nutrition_avg.avg_calories}</strong></span>
                    <span>Sodium: <strong>{stats.search_nutrition_avg.avg_sodium}mg</strong></span>
                  </div>
                </Card>

                {/* 2. TOP TAGS (CATEGORIES) */}
                <Card className="md:col-span-1 shadow-sm border-slate-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-slate-700 flex items-center gap-2">
                        <Tag className="h-4 w-4 text-pink-500"/> Top Categories
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 pt-4">
                    {stats.top_tags.map((tag, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                            <span className="text-sm text-slate-600 capitalize truncate max-w-[150px]" title={tag.name}>
                              {tag.name.replace(/-/g, ' ')}
                            </span>
                            <div className="flex items-center gap-2 flex-1 justify-end ml-4">
                                <div className="h-2 bg-pink-100 rounded-full w-20 overflow-hidden">
                                    <div className="h-full bg-pink-400 rounded-full" style={{ width: `${Math.min((tag.count / stats.total_searches) * 100, 100)}%` }}></div>
                                </div>
                                <span className="text-xs font-bold text-pink-600 w-6 text-right">{tag.count}</span>
                            </div>
                        </div>
                    ))}
                  </CardContent>
                </Card>

                {/* 3. TOP FILTERS (PREFERENCES) */}
                <Card className="md:col-span-1 shadow-sm border-slate-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-bold text-slate-700 flex items-center gap-2">
                        <Filter className="h-4 w-4 text-cyan-500"/> Preferred Filters
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-4">
                    {stats.top_filters.length > 0 ? stats.top_filters.map((filter, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 transition-colors">
                            <span className="text-sm text-slate-600 capitalize">{filter.name.replace(/_/g, ' ')}</span>
                            <Badge variant="secondary" className="bg-cyan-50 text-cyan-700 hover:bg-cyan-100 border-cyan-100">
                                {filter.count} uses
                            </Badge>
                        </div>
                    )) : (
                        <div className="flex flex-col items-center justify-center h-40 text-slate-400">
                           <Filter className="h-8 w-8 mb-2 opacity-20"/>
                           <span className="text-sm italic">No filters used yet</span>
                        </div>
                    )}
                  </CardContent>
                </Card>

              </div>
            </div>

            {/* =================================================================================
                SECTION 3: DEEP DIVE (Ingredients & Conversion)
               ================================================================================= */}
            <div className="grid gap-6 md:grid-cols-12">

              {/* LEFT: INGREDIENTS CHART */}
              <Card className="md:col-span-8 shadow-sm border-slate-200">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <div>
                    <CardTitle className="text-lg font-bold text-slate-800 flex items-center gap-2">
                      <Sprout className="h-5 w-5 text-green-600"/> Flavor Profile
                    </CardTitle>
                    <CardDescription>Top ingredients appearing in your searches</CardDescription>
                  </div>
                  <Badge variant="secondary" className="gap-1 bg-slate-100 text-slate-600 hover:bg-slate-200">
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

              {/* RIGHT: ACTIVITY & SEARCH TIME */}
              <div className="md:col-span-4 flex flex-col gap-4">

                {/* AVG SEARCH TIME CARD */}
                <Card className="shadow-sm border-slate-200 bg-slate-50">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className="text-slate-500 text-xs uppercase font-bold tracking-wider mb-1">Avg Cooking Time</p>
                            <div className="flex items-baseline gap-2">
                                <p className="text-2xl font-bold text-slate-800">{stats.avg_recipe_time}</p>
                                <span className="text-sm text-slate-500">min</span>
                            </div>
                        </div>
                        <div className="h-10 w-10 rounded-full bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                            <Clock className="h-5 w-5 text-slate-600" />
                        </div>
                    </CardContent>
                </Card>

                {/* Conversion Card */}
                <Card className="flex-1 shadow-sm border-slate-200 flex flex-col">
                  <CardHeader className="pb-0">
                    <CardTitle className="text-lg font-bold text-slate-800 flex items-center gap-2">
                        <Zap className="h-5 w-5 text-amber-500"/> Activity Ratio
                    </CardTitle>
                    <CardDescription>Search vs. Transform</CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col items-center justify-center min-h-[160px]">
                    <div className="h-[140px] w-full relative">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={conversionData}
                            cx="50%"
                            cy="50%"
                            innerRadius={40}
                            outerRadius={60}
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
                         <span className="text-xl font-bold text-slate-800">{stats.conversion_rate}%</span>
                      </div>
                    </div>
                    <div className="flex w-full justify-between px-2 mt-2 text-xs text-slate-500">
                        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-500"/> Transformed</span>
                        <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-slate-200"/> Standard Search</span>
                    </div>
                  </CardContent>
                </Card>

              </div>
            </div>

            {/* =================================================================================
                SECTION 4: HIGHLIGHTS & RANKINGS
               ================================================================================= */}

            {/* BIGGEST WIN ROW */}
            <Card className="bg-gradient-to-r from-amber-50 via-white to-white border-amber-200 shadow-sm relative overflow-hidden">
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

            {/* RANKING ROW */}
            <div className="grid gap-6 md:grid-cols-2">

                {/* BEST RECIPES */}
                <Card className="border-emerald-100 bg-white shadow-sm">
                    <CardHeader className="pb-2 border-b border-slate-50">
                        <CardTitle className="text-sm font-semibold text-emerald-700 flex items-center gap-2">
                            <ThumbsUp className="h-4 w-4" /> Top 5 Healthiest Picks
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <RecipeList
                            recipes={stats.top_5_healthy_recipes}
                            colorClass="text-emerald-700 bg-emerald-50"
                            scoreColor="text-emerald-600"
                        />
                    </CardContent>
                </Card>

                {/* WORST RECIPES */}
                <Card className="border-red-100 bg-white shadow-sm">
                    <CardHeader className="pb-2 border-b border-slate-50">
                        <CardTitle className="text-sm font-semibold text-red-700 flex items-center gap-2">
                            <ThumbsDown className="h-4 w-4" /> 5 Needs Improvement
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <RecipeList
                            recipes={stats.top_5_unhealthy_recipes}
                            colorClass="text-red-700 bg-red-50"
                            scoreColor="text-red-600"
                        />
                    </CardContent>
                </Card>

            </div>

          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

// --- Helper Component pour la liste de recettes ---
function RecipeList({ recipes, colorClass, scoreColor }: { recipes: RecipeRanking[], colorClass: string, scoreColor: string }) {
    if (!recipes || recipes.length === 0) {
        return <div className="text-sm text-slate-400 italic text-center py-4">No data available</div>
    }

    return (
        <div className="space-y-3">
            {recipes.map((recipe, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm group hover:bg-slate-50 p-2 rounded-lg transition-colors">
                    <div className="flex items-center gap-3 overflow-hidden">
                        <span className={cn("flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold shrink-0", colorClass)}>
                            {idx + 1}
                        </span>
                        <span className="font-medium text-slate-700 truncate" title={recipe.name}>
                            {recipe.name}
                        </span>
                    </div>
                    <span className={cn("font-bold ml-2", scoreColor)}>
                        {recipe.health_score}
                    </span>
                </div>
            ))}
        </div>
    )
}
