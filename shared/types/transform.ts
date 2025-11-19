/**
 * Shared type definitions for Recipe Transformation
 */

export interface TransformConstraints {
  no_lactose?: boolean
  no_gluten?: boolean
  no_nuts?: boolean
  vegetarian?: boolean
  vegan?: boolean
  
  increase_protein?: boolean
  decrease_carbs?: boolean
  decrease_calories?: boolean
  decrease_sodium?: boolean
}

export interface TransformRequest {
  recipe_id: number
  goal: string  // "healthier", "low-carb", "high-protein", etc.
  constraints?: TransformConstraints
}

export interface Substitution {
  original_ingredient: string
  substitute_ingredient: string
  original_quantity?: number
  substitute_quantity?: number
  reason: string
}

export interface NutritionDelta {
  calories: number
  protein_g: number
  fat_g: number
  carbs_g: number
  fiber_g: number
  sodium_mg: number
  score_health: number
}

export interface TransformResponse {
  recipe_id: number
  original_name: string
  transformed_name: string
  
  substitutions: Substitution[]
  
  nutrition_before: Record<string, number>
  nutrition_after: Record<string, number>
  delta: NutritionDelta
  
  success: boolean
  message?: string
}

