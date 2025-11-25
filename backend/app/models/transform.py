from enum import Enum
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

class TransformationType(Enum):
    ADD = 0,
    DELETE = 1,
    SUBSTITUTION = 2

class TransformConstraints(BaseModel):
    # Constraints for recipe transformation
    transformation : TransformationType
    no_lactose: Optional[Optional [bool]] = False
    no_gluten: Optional[Optional [bool]] = False
    no_nuts: Optional[Optional [bool]] = False
    vegetarian: Optional [bool] = False
    vegan: Optional [bool] = False
    
    increase_protein: Optional [bool] = False
    decrease_sugar :Optional [bool] = False
    decrease_protein: Optional [bool] = False
    decrease_carbs: Optional [bool] = False
    decrease_calories: Optional [bool] = False
    decrease_sodium: Optional [bool] = False

# recipe object request
class Recipe(BaseModel):
    name: str
    ingredients:  List[str]
    quantity_ingredients :  List[str]
    minutes: float
    steps: List[str]

class TransformRequest(BaseModel):
    # Transform request body
    recipe: Recipe
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
    
    nutrition_before: float ## nutri score before
    nutrition_after: float ## nutri score after 
    delta: NutritionDelta
    
    success: bool
    message: Optional[str] = None

