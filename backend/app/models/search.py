from typing import Optional, Dict, Any, List
from recipe import NutritionDetailed, Recipe
from pydantic import BaseModel, Field

class NumericFilter(BaseModel):
    name: str                 # "minutes", "n_steps", "servings", ...
    operator: str             # ">", ">=", "<", "<=", "="
    value: float | int        # valeur numérique


class SearchFilters(BaseModel):
    numeric_filters: Optional[List[NumericFilter]] = Field(
        default_factory=list,
        description="List of numeric filters applied to metadata fields"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Required tags for filtering (must contain all)"
    )
    include_ingredients: Optional[List[str]] = Field(
        default_factory=list,
        description="Ingredients that must be included in the recipe"
    )
    exclude_ingredients: Optional[List[str]] = Field(
        default_factory=list,
        description="Ingredients that must NOT be in the recipe"
    )

class SearchRequest(BaseModel):
    user: str
    query: str = Field(..., description="Natural language search query")
    k: int = Field(default=10, ge=1, le=50, description="Number of top-k results to return")
    filters: Optional[SearchFilters] = None

### OLD ResponseModel, use Recipe instead to synchronize with group 1
# class SearchResult(BaseModel): 
#     # Single search result
#     id: int
#     name: str
#     description: Optional[str] = None
#     similarity: float
#     nutrition: Optional[NutritionDetailed] = None  ## OBJET NUTRITIONDETAIL GROUP 1
#     score_health: Optional[float] = None
#     rating: Optional[float] = None
#     rating_avg: Optional[float] = None
#     tags: list[str] = Field(default_factory=list)
#     ingredients : list[str]
#     steps : str
#     minute: int
#     nb_ingredients: int
#     nb_steps : int


class SearchResponse(BaseModel):
    # Search response
    results: list[Recipe]
    query: str
    total_found: int
    execution_time_ms: float
    status: str

