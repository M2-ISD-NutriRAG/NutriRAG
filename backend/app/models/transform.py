from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class TransformConstraints(BaseModel):
    # Constraints for recipe transformation
    no_lactose: bool = False
    no_gluten: bool = False
    no_nuts: bool = False
    vegetarian: bool = False
    vegan: bool = False
    
    increase_protein: bool = False
    decrease_carbs: bool = False
    decrease_calories: bool = False
    decrease_sodium: bool = False


class TransformRequest(BaseModel):
    # Transform request body
    recipe_id: int
    goal: str = Field(..., description="healthier, low-carb, high-protein, etc.")
    constraints: Optional[TransformConstraints] = None


class Substitution(BaseModel):
    # Single ingredient substitution
    original_ingredient: str
    substitute_ingredient: str
    original_quantity: Optional[float] = None
    substitute_quantity: Optional[float] = None
    reason: str


class NutritionDelta(BaseModel):
    # Changes in nutrition values
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    sodium_mg: float
    score_health: float


class TransformResponse(BaseModel):
    # Transform response
    recipe_id: int
    original_name: str
    transformed_name: str
    
    substitutions: List[Substitution]
    
    nutrition_before: Dict[str, float]
    nutrition_after: Dict[str, float]
    delta: NutritionDelta
    
    success: bool
    message: Optional[str] = None

