from enum import Enum
from typing import Optional, List
from pydantic import BaseModel  # type: ignore


class TransformationType(Enum):
    ADD = 0
    DELETE = 1
    SUBSTITUTION = 2


class TransformConstraints(BaseModel):
    # Constraints for recipe transformation
    transformation: TransformationType
    no_lactose: Optional[bool] = False
    no_gluten: Optional[bool] = False
    no_nuts: Optional[bool] = False
    vegetarian: Optional[bool] = False
    vegan: Optional[bool] = False

    increase_protein: Optional[bool] = False
    decrease_sugar: Optional[bool] = False
    decrease_protein: Optional[bool] = False
    decrease_carbs: Optional[bool] = False
    decrease_calories: Optional[bool] = False
    decrease_sodium: Optional[bool] = False


# recipe object request
class Recipe(BaseModel):
    name: str
    ingredients: List[str]
    quantity_ingredients: List[str]
    minutes: float
    steps: List[str]


class TransformRequest(BaseModel):
    # Transform request body
    recipe: Recipe
    ingredients_to_remove: Optional[List[str]] = None
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
    calories: float = 0.0
    protein_g: float = 0.0
    saturated_fats_g: float = 0.0
    fat_g: float = 0.0 
    carb_g: float = 0.0 
    fiber_g: float = 0.0 
    sodium_mg: float = 0.0 
    sugar_g: float = 0.0 
    score_health: float = 0.0 


class TransformResponse(BaseModel):
    # Transform response
    recipe: Recipe
    original_name: str
    transformed_name: str
    
    substitutions: Optional[List[Substitution]]
    
    nutrition_before: Optional[NutritionDelta] ## nutri score before
    nutrition_after: Optional[NutritionDelta] ## nutri score after 
    
    success: bool
    message: Optional[str] = None
