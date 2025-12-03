/**
 * Shared type definitions for Analytics & ML
 */

// ============================================
// Types Backend (correspondent à analytics.py)
// ============================================

export interface Cluster {
  cluster_id: number
  label: string
  size: number
  examples: string[]
  centroid?: number[]
}

export interface ClusterResponse {
  clusters: Cluster[]
  total_clusters: number
  algorithm: string
  feature_type: string
}

export interface KPI {
  name: string
  value: number
  unit: string
  description: string
  team?: string
}

export interface KPIResponse {
  kpis: KPI[]
  timestamp: string
}

// ============================================
// Types additionnels pour le Frontend (pas encore dans backend)
// ============================================

export type MetricType = 'calories' | 'protein' | 'carbs' | 'fat' | 'score_health' | 'rating'

export interface Distribution {
  metric: MetricType
  bins: number[]
  counts: number[]
  mean: number
  median: number
  std: number
}

export interface CorrelationMatrix {
  metrics: string[]
  matrix: number[][]
}

// Dashboard-specific types (Frontend)
export interface AnalyticsKPIs {
  kpis: Array<{
    name: string
    value: number | string
    trend?: number
    description?: string
    unit?: string
  }>
}

export interface AnalyticsUsage {
  total_searches: number
  total_transformations: number
  unique_users: number
  avg_response_time: number
  period: string
}

export interface PopularRecipe {
  recipe: any
  view_count: number
  transformation_count: number
  avg_rating?: number
}

export interface PopularRecipesResponse {
  recipes: PopularRecipe[]
}

