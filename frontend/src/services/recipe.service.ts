import { apiClient } from '@/lib/api'
import { Recipe } from '@shared/types'

export const recipeService = {
  async getRecipe(id: number): Promise<Recipe> {
    const response = await apiClient.get(`/api/recipes/${id}`)
    return response.data
  },

  async getRecipes(params?: any): Promise<Recipe[]> {
    const response = await apiClient.get('/api/recipes', { params })
    return response.data
  },

  async getRandomRecipes(count: number = 5): Promise<Recipe[]> {
    const response = await apiClient.get('/api/recipes', {
      params: { limit: count, random: true }
    })
    return response.data
  },
}

export default recipeService

