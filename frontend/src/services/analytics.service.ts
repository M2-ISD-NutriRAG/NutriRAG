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

export interface RecipeRanking {
  name: string;
  health_score: number;
}

export interface DashboardStats {
  total_searches: number;
  total_transformations: number;
  conversion_rate: number;
  total_calories_saved: number;
  total_protein_gained: number;
  avg_health_score_gain: number;
  ingredient_diversity_index: number;
  top_ingredients: TopIngredient[];
  top_diet_constraint: string;
  biggest_optimization: BiggestWin | null;
  top_5_healthy_recipes: RecipeRanking[];
  top_5_unhealthy_recipes: RecipeRanking[];
  avg_recipe_time: number;
  avg_time_saved: number;
}

export interface TransformationDetail {
  original_name: string;
  transformed_name: string;
  delta_calories: number;
  delta_protein: number;
  delta_fat: number;
  delta_carbs: number;
  delta_fiber: number;
  delta_sugar: number;
  delta_sodium: number;
  delta_health_score: number;
}

export interface ConversationStats {
  total_messages: number;
  total_transformations: number;
  transformations_list: TransformationDetail[];
}

export const analyticsService = {
  getDashboardData: async (userId: string): Promise<DashboardStats> => {
    const response = await apiClient.get(`api/analytics/kpi?user_id=${userId}`);
    return response.data;
  },

  getConversationStats: async (conversationId: string): Promise<ConversationStats> => {
    const response = await apiClient.get(`api/analytics/conversation/${conversationId}`);
    return response.data;
  }
}
