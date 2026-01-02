from enum import Enum
from typing import Optional, List


class TransformationType(Enum):
    ADD = 0
    DELETE = 1
    SUBSTITUTION = 2


class TransformConstraints:
    # Constraints for recipe transformation
    def __init__(
        self,
        transformation: TransformationType,
        no_lactose: Optional[bool] = False,
        no_gluten: Optional[bool] = False,
        no_nuts: Optional[bool] = False,
        vegetarian: Optional[bool] = False,
        vegan: Optional[bool] = False,
        increase_protein: Optional[bool] = False,
        decrease_sugar: Optional[bool] = False,
        decrease_protein: Optional[bool] = False,
        decrease_carbs: Optional[bool] = False,
        decrease_calories: Optional[bool] = False,
        decrease_sodium: Optional[bool] = False,
    ):
        self.transformation = transformation
        self.no_lactose = no_lactose
        self.no_gluten = no_gluten
        self.no_nuts = no_nuts
        self.vegetarian = vegetarian
        self.vegan = vegan
        self.increase_protein = increase_protein
        self.decrease_sugar = decrease_sugar
        self.decrease_protein = decrease_protein
        self.decrease_carbs = decrease_carbs
        self.decrease_calories = decrease_calories
        self.decrease_sodium = decrease_sodium


class Recipe:
    def __init__(
        self,
        id: int,
        name: str,
        serving_size: float,
        servings: float,
        health_score: float,
        ingredients: List[str],
        quantity_ingredients: List[str],
        minutes: float,
        steps: List[str],
    ):
        self.id = id
        self.name = name
        self.serving_size = serving_size
        self.servings = servings
        self.health_score = health_score
        self.ingredients = ingredients
        self.quantity_ingredients = quantity_ingredients
        self.minutes = minutes
        self.steps = steps


class TransformRequest:
    # Transform request body
    def __init__(
        self,
        recipe: Recipe,
        ingredients_to_remove: Optional[List[str]] = None,
        constraints: Optional[TransformConstraints] = None,
    ):
        self.recipe = recipe
        self.ingredients_to_remove = ingredients_to_remove
        self.constraints = constraints


class Substitution:
    # Single ingredient substitution
    def __init__(
        self,
        original_ingredient: str,
        substitute_ingredient: str,
        original_quantity: Optional[float] = None,
        substitute_quantity: Optional[float] = None,
        reason: str = "",
    ):
        self.original_ingredient = original_ingredient
        self.substitute_ingredient = substitute_ingredient
        self.original_quantity = original_quantity
        self.substitute_quantity = substitute_quantity
        self.reason = reason


class NutritionDelta:
    # Changes in nutrition values
    def __init__(
        self,
        calories: float = 0.0,
        protein_g: float = 0.0,
        saturated_fats_g: float = 0.0,
        fat_g: float = 0.0,
        carb_g: float = 0.0,
        fiber_g: float = 0.0,
        sodium_mg: float = 0.0,
        sugar_g: float = 0.0,
        iron_mg : float = 0.0,
        calcium_mg: float = 0.0,
        magnesium_mg: float = 0.0,
        potassium_mg: float = 0.0,
        vitamin_c_mg: float = 0.0,
        health_score: float = 0.0,
    ):
        self.calories = calories
        self.protein_g = protein_g
        self.saturated_fats_g = saturated_fats_g
        self.fat_g = fat_g
        self.carb_g = carb_g
        self.fiber_g = fiber_g
        self.sodium_mg = sodium_mg
        self.sugar_g = sugar_g
        self.calcium_mg
        self.iron_mg = iron_mg
        self.magnesium_mg = magnesium_mg
        self.potassium_mg = potassium_mg
        self.vitamin_c_mg = vitamin_c_mg
        self.health_score = health_score


class TransformResponse:
    # Transform response
    def __init__(
        self,
        recipe: Recipe,
        original_name: str,
        transformed_name: str,
        substitutions: Optional[List[Substitution]] = None,
        nutrition_before: Optional[NutritionDelta] = None,
        nutrition_after: Optional[NutritionDelta] = None,
        success: bool = True,
        message: Optional[str] = None,
    ):
        self.recipe = recipe
        self.original_name = original_name
        self.transformed_name = transformed_name
        self.substitutions = substitutions
        self.nutrition_before = nutrition_before
        self.nutrition_after = nutrition_after
        self.success = success
        self.message = message
