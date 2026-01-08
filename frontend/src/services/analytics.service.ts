import { apiClient } from '@/lib/api'

export interface TopIngredient {
  name: string;
  count: number;
}

export interface BiggestWin {
  original_name: string;
  transformed_name: string;
  health_score_delta: number;
}

// L'interface principale mise à jour
export interface DashboardStats {
  // Volume & Conversion
  total_searches: number;
  total_transformations: number;
  conversion_rate: number;

  // Nutrition & Santé
  total_calories_saved: number;
  total_protein_gained: number;      // Nouveau
  avg_health_score_gain: number;

  // Diversité & Contenu
  ingredient_diversity_index: number; // Nouveau
  top_ingredients: TopIngredient[];   // Nouveau
  top_diet_constraint: string;

  // Gamification
  biggest_optimization: BiggestWin | null; // Nouveau
}

export const analyticsService = {
  getDashboardData: async (userId: string = 'DOG'): Promise<DashboardStats> => {
    // On suppose que l'endpoint ignore l'ID ou l'utilise via query param
    const response = await apiClient.get(`api/analytics/kpi?user_id=${userId}`);
    return response.data;
  }
}
