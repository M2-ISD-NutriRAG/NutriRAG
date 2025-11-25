import { apiClient } from '@/lib/api'
import { PopularRecipesResponse } from '@shared/types'
// import { AnalyticsUsage } from '@shared/types/analytics' --> unused

// Types pour le frontend (pas encore dans backend)
export interface KPIData {
  total_searches: number
  total_transformations: number
  active_users: number
  avg_response_time: number
}

export interface UsageStats {
  date: string
  searches: number
  transformations: number
  users: number
}

export const analyticsService = {
  async getKPIs(): Promise<KPIData> {
    const response = await apiClient.get('/api/analytics/kpi')
    return response.data
  },

  async getUsageStats(period: string = '7d'): Promise<UsageStats[]> {
    const response = await apiClient.get('/api/analytics/usage', {
      params: { period }
    })
    return response.data
  },

  async getPopularRecipes(limit: number = 10): Promise<PopularRecipesResponse> {
    const response = await apiClient.get('/api/analytics/popular', {
      params: { limit }
    })
    return response.data
  },
}

export default analyticsService

