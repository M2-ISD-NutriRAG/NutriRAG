from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Optional, Any
import json


class NutritionDetailed(BaseModel):
    # Detailed nutrition information
    energy_kcal_100g: Optional[float] = None
    protein_g_100g: Optional[float] = None
    fat_g_100g: Optional[float] = None
    saturated_fats_g_100g: Optional[float] = None
    carbs_g_100g: Optional[float] = None
    fiber_g_100g: Optional[float] = None
    sugar_g_100g: Optional[float] = None
    sodium_mg_100g: Optional[float] = None

    # Optional micronutrients
    calcium_mg_100g: Optional[float] = None
    iron_mg_100g: Optional[float] = None
    magnesium_mg_100g: Optional[float] = None
    potassium_mg_100g: Optional[float] = None
    vitamin_c_mg_100g: Optional[float] = None


class Recipe(BaseModel):
    # Complete recipe model
    id: int
    name: str
    description: str
    minutes: int
    n_steps: int
    n_ingredients: int
    servings: int
    serving_size: int
    

    # Arrays
    tags: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    search_terms: List[str] = Field(default_factory=list)
    ingredients: List[str] = Field(default_factory=list)
    ingredients_with_quantities: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)

    # Nutrition
    nutrition: Optional[List[float]] = None  # Original from Food.com
    nutrition_detailed: Optional[NutritionDetailed] = None  # Calculated by Team 1


    # Scores
    score_sante: Optional[float] = None

    # Validation to normalize field names because Snowflake these fields are uppercase
    @model_validator(mode="before")
    @classmethod
    def normalize_field_names(cls, data):
        """Normalize all field names to lowercase to accept both 'name' and 'NAME'."""
        if isinstance(data, dict):
            return {key.lower(): value for key, value in data.items()}
        return data

    @field_validator(
        "tags",
        "filters",
        "search_terms",
        "steps",
        "ingredients_with_quantities",
        "nutrition",
        mode="before",
    )
    @classmethod
    def parse_json_string(cls, v: Any) -> Any:
        """Parse JSON strings from Snowflake if they look like JSON arrays."""
        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


class RecipeListResponse(BaseModel):
    # Response for list of recipes
    recipes: List[Recipe]
    total: int
    skip: int
    limit: int
