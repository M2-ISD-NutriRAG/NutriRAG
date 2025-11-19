/**
 * Shared TypeScript types for NutriRAG - Recipe Domain
 */

// Nutrition détaillée (correspond au backend NutritionDetailed)
export interface NutritionDetailed {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  saturated_fat_g: number;
  sodium_mg: number;
  sugar_g?: number;
  fiber_g?: number;
  
  // Micronutriments optionnels
  calcium_mg?: number;
  iron_mg?: number;
  magnesium_mg?: number;
  potassium_mg?: number;
  vitamin_c_mg?: number;
}

// Ingrédient parsé (correspond au backend IngredientParsed)
export interface IngredientParsed {
  quantity?: number;
  unit?: string;
  name: string;
  ndb_no?: number;  // Link to cleaned_ingredients
}

// Recette complète (correspond au backend Recipe)
export interface Recipe {
  id: number;
  name: string;
  description?: string;
  minutes: number;
  n_steps: number;
  n_ingredients: number;
  
  // Arrays
  tags: string[];
  ingredients_raw: string[];
  ingredients_parsed?: IngredientParsed[];
  steps: string[];
  
  // Nutrition
  nutrition_original?: number[];  // Original from Food.com [calories, fat, sugar, sodium, protein, sat_fat, carbs]
  nutrition_detailed?: NutritionDetailed;  // Calculated by Équipe 1
  
  // Scores
  score_health?: number;
  rating_avg?: number;
  rating_count?: number;
}

// Type alias pour compatibilité
export type Ingredient = IngredientParsed;
