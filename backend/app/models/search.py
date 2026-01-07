from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field

try:
    from app.models.recipe import Recipe
except (ImportError, ModuleNotFoundError):
    # Fallback for Snowflake - assume recipe module is available in same context
    from recipe import Recipe


class NumericFilter(BaseModel):
    name: str  # "minutes", "n_steps", "servings", ...
    operator: str  # ">", ">=", "<", "<=", "="
    value: float | int  # numeric value


class SearchFilters(BaseModel):
    numeric_filters: Optional[List[NumericFilter]] = Field(
        default_factory=list,
        description="List of numeric filters applied to metadata fields",
    )
    dietary_filters: Optional[
        List[
            Literal[
                "amish",
                "dairy_free",
                "diabetic",
                "egg_free",
                "gluten_free",
                "halal",
                "kosher",
                "low_calorie",
                "low_carb",
                "low_cholesterol",
                "low_fat",
                "low_protein",
                "low_saturated_fat",
                "low_sodium",
                "no_shell_fish",
                "non_alcoholic",
                "nut_free",
                "vegan",
                "vegetarian",
            ]
        ]
    ] = Field(
        default_factory=list,
        description="Required tags for filtering (must contain all)",
    )
    include_ingredients: Optional[List[str]] = Field(
        default_factory=list,
        description="Ingredients that must be included in the recipe (must contain all)",
    )
    exclude_ingredients: Optional[List[str]] = Field(
        default_factory=list,
        description="Ingredients that must NOT be in the recipe (must not contain any)",
    )
    any_ingredients: Optional[List[str]] = Field(
        default_factory=list,
        description="At least one of these ingredients must be in the recipe",
    )


class SearchRequest(BaseModel):
    user: str
    query: str = Field(..., description="Natural language search query")
    k: int = Field(default=10, description="Number of top-k results to return")
    filters: Optional[SearchFilters] = None


class SearchResponse(BaseModel):
    # Search response
    results: List[Recipe]
    query: str
    total_found: int
    execution_time_ms: float
    status: str
