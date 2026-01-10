from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class TransformationType(Enum):
    ADD = 0
    DELETE = 1
    SUBSTITUTION = 2


class TransformConstraints(BaseModel):
    # Constraints for recipe transformation
    transformation: TransformationType
    no_lactose: bool = False
    no_gluten: bool = False
    no_nuts: bool = False
    vegetarian: bool = False
    vegan: bool = False
    increase_protein: bool = False
    decrease_sugar: bool = False
    decrease_protein: bool = False
    decrease_carbs: bool = False
    decrease_calories: bool = False
    decrease_sodium: bool = False
    decrease_satfat: bool = False


class Recipe(BaseModel):
    id: int
    name: str
    serving_size: float
    servings: float
    health_score: float
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
    reason: str = ""


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
    iron_mg: float = 0.0
    calcium_mg: float = 0.0
    magnesium_mg: float = 0.0
    potassium_mg: float = 0.0
    vitamin_c_mg: float = 0.0
    health_score: float = 0.0


class TransformResponse(BaseModel):
    # Transform response
    recipe: Recipe
    original_name: str
    transformed_name: str
    substitutions: Optional[List[Substitution]] = None
    nutrition_before: Optional[NutritionDelta] = None
    nutrition_after: Optional[NutritionDelta] = None
    success: bool = True
    message: Optional[str] = None
