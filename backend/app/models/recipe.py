from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IngredientParsed(BaseModel):
    # Parsed ingredient with quantity, unit, and name
    quantity: Optional[float] = None
    unit: Optional[str] = None
    name: str
    ndb_no: Optional[int] = None  # Link to cleaned_ingredients


class NutritionDetailed(BaseModel):
    # Detailed nutrition information
    calories: float
    protein_g: float
    fat_g: float
    saturated_fat_g: float
    carbs_g: float
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: float
    
    # Optional micronutrients
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None
    magnesium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    vitamin_c_mg: Optional[float] = None


class Recipe(BaseModel):
    # Complete recipe model
    id: int
    name: str
    description: Optional[str] = None
    minutes: int
    n_steps: int
    n_ingredients: int
    
    # Arrays
    tags: List[str] = Field(default_factory=list)
    ingredients_raw: List[str] = Field(default_factory=list)
    ingredients_parsed: Optional[List[IngredientParsed]] = None
    steps: List[str] = Field(default_factory=list)
    
    # Nutrition
    nutrition_original: Optional[List[float]] = None  # Original from Food.com
    nutrition_detailed: Optional[NutritionDetailed] = None  # Calculated by Équipe 1
    
    # Scores
    score_health: Optional[float] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None


class RecipeListResponse(BaseModel):
    # Response for list of recipes
    recipes: List[Recipe]
    total: int
    skip: int
    limit: int

