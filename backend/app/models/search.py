from typing import Optional, Dict
from pydantic import BaseModel, Field, model_validator


class SearchFilters(BaseModel):
    """
    Pydantic model for filtering recipe search results based on various criteria.

    This model provides comprehensive filtering options for recipes including:
    - Nutritional information (calories, fats, protein, carbs, etc.)
    - Recipe attributes (cooking time, steps, ingredients count, servings)
    - Tags and ingredients inclusion/exclusion
    - Rating-based filters
    - Advanced filtering options

    All min/max pairs are validated to ensure logical ranges where minimum
    values don't exceed maximum values.

    Attributes:
        calories_min (Optional[float]): Minimum calories per serving (>= 0)
        calories_max (Optional[float]): Maximum calories per serving (>= 0)
        total_fat_min (Optional[float]): Minimum total fat in grams (>= 0)
        total_fat_max (Optional[float]): Maximum total fat in grams (>= 0)
        sugar_min (Optional[float]): Minimum sugar content in grams (>= 0)
        sugar_max (Optional[float]): Maximum sugar content in grams (>= 0)
        sodium_min (Optional[float]): Minimum sodium content in mg (>= 0)
        sodium_max (Optional[float]): Maximum sodium content in mg (>= 0)
        protein_min (Optional[float]): Minimum protein content in grams (>= 0)
        protein_max (Optional[float]): Maximum protein content in grams (>= 0)
        saturated_fat_min (Optional[float]): Minimum saturated fat in grams (>= 0)
        saturated_fat_max (Optional[float]): Maximum saturated fat in grams (>= 0)
        carbs_min (Optional[float]): Minimum carbohydrates in grams (>= 0)
        carbs_max (Optional[float]): Maximum carbohydrates in grams (>= 0)
        minutes_min (Optional[int]): Minimum cooking time in minutes (>= 0)
        minutes_max (Optional[int]): Maximum cooking time in minutes (>= 0)
        n_steps_min (Optional[int]): Minimum number of recipe steps (>= 0)
        n_steps_max (Optional[int]): Maximum number of recipe steps (>= 0)
        n_ingredients_min (Optional[int]): Minimum number of ingredients (>= 0)
        n_ingredients_max (Optional[int]): Maximum number of ingredients (>= 0)
        servings_min (Optional[int]): Minimum number of servings (>= 0)
        servings_max (Optional[int]): Maximum number of servings (>= 0)
        serving_size_min (Optional[float]): Minimum serving size (>= 0)
        serving_size_max (Optional[float]): Maximum serving size (>= 0)
        tags_include (Optional[list[str]]): Tags that must be present in recipes
        tags_exclude (Optional[list[str]]): Tags that must not be present in recipes
        rating_avg_min (Optional[float]): Minimum average rating (0-5 scale)
        rating_avg_max (Optional[float]): Maximum average rating (0-5 scale)
        rating_count_min (Optional[int]): Minimum number of ratings required (>= 0)
        ingredients_include (Optional[list[str]]): Ingredients that must be present
        ingredients_exclude (Optional[list[str]]): Ingredients that must not be present

    Raises:
        ValueError: If any minimum value exceeds its corresponding maximum value

    Example:
        >>> filters = SearchFilters(
        ...     calories_min=200,
        ...     calories_max=500,
        ...     tags_include=["vegetarian"],
        ...     rating_avg_min=4.0
        ... )
    """

    # Nutrition filters
    calories_min: Optional[float] = Field(None, ge=0)
    calories_max: Optional[float] = Field(None, ge=0)
    total_fat_min: Optional[float] = Field(None, ge=0)
    total_fat_max: Optional[float] = Field(None, ge=0)
    sugar_min: Optional[float] = Field(None, ge=0)
    sugar_max: Optional[float] = Field(None, ge=0)
    sodium_min: Optional[float] = Field(None, ge=0)
    sodium_max: Optional[float] = Field(None, ge=0)
    protein_min: Optional[float] = Field(None, ge=0)
    protein_max: Optional[float] = Field(None, ge=0)
    saturated_fat_min: Optional[float] = Field(None, ge=0)
    saturated_fat_max: Optional[float] = Field(None, ge=0)
    carbs_min: Optional[float] = Field(None, ge=0)
    carbs_max: Optional[float] = Field(None, ge=0)

    # Recipe attributes filters
    minutes_min: Optional[int] = Field(None, ge=0)
    minutes_max: Optional[int] = Field(None, ge=0)
    n_steps_min: Optional[int] = Field(None, ge=0)
    n_steps_max: Optional[int] = Field(None, ge=0)
    n_ingredients_min: Optional[int] = Field(None, ge=0)
    n_ingredients_max: Optional[int] = Field(None, ge=0)
    servings_min: Optional[int] = Field(None, ge=0)
    servings_max: Optional[int] = Field(None, ge=0)
    serving_size_min: Optional[float] = Field(None, ge=0)
    serving_size_max: Optional[float] = Field(None, ge=0)

    # Tags and ingredients filters
    tags_include: Optional[list[str]] = None
    tags_exclude: Optional[list[str]] = None
    ingredients_include: Optional[list[str]] = None
    ingredients_exclude: Optional[list[str]] = None

    # Rating filters
    rating_avg_min: Optional[float] = Field(None, ge=0, le=5)
    rating_avg_max: Optional[float] = Field(None, ge=0, le=5)
    rating_count_min: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_min_max_ranges(self) -> "SearchFilters":
        """Validate that min values don't exceed max values for all range fields."""
        field_bases = [
            "calories",
            "total_fat",
            "sugar",
            "sodium",
            "protein",
            "saturated_fat",
            "carbs",
            "minutes",
            "n_steps",
            "n_ingredients",
            "servings",
            "serving_size",
            "rating_avg",
        ]

        for field_base in field_bases:
            min_val = getattr(self, f"{field_base}_min")
            max_val = getattr(self, f"{field_base}_max")
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValueError(
                    f"{field_base}_min cannot be greater than {field_base}_max"
                )

        return self


class SearchRequest(BaseModel):
    """
    Represents a search request for querying nutritional data.

    This model defines the structure for search requests that can be used to query
    nutritional information with natural language queries, optional filtering,
    and result limiting capabilities.

    Args:
        query (str): Natural language search query describing what the user is looking for.
            This field is required and cannot be empty.
        filters (Optional[SearchFilters]): Optional filters to narrow down search results.
            Can include dietary restrictions, nutritional ranges, or other criteria.
            Defaults to None if no specific filters are needed.
        limit (int): Maximum number of search results to return. Must be between 1 and 50.
            Defaults to 10 results to balance performance and usefulness.

    Example:
        >>> search_request = SearchRequest(
        ...     query="high protein breakfast options",
        ...     filters=SearchFilters(max_calories=300),
        ...     limit=5
        ... )
    """

    query: str = Field(..., min_length=1, description="Natural language search query")
    filters: Optional[SearchFilters] = Field(
        None, description="Optional search filters"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")


class SearchResult(BaseModel):
    """
    Represents a search result for a recipe with comprehensive nutritional and cooking information.

    This model encapsulates all relevant details about a recipe returned from a search query,
    including basic information, nutritional data, cooking instructions, and similarity scoring.

    Attributes:
        id (int): Unique identifier for the recipe
        name (str): Display name of the recipe (minimum 1 character)
        description (Optional[str]): Detailed description of the recipe
        tags (list[str]): List of category tags associated with the recipe
        minutes (Optional[int]): Total cooking time in minutes (non-negative)
        nutrition (Optional[Dict[str, float]]): Dictionary containing nutritional values
        score_health (Optional[float]): Health score rating from 0 to 1 (higher is healthier)
        n_ingredients (Optional[int]): Total count of ingredients required (non-negative)
        ingredients (Optional[list[str]]): List of ingredient names/descriptions
        n_steps (Optional[int]): Total number of cooking steps (non-negative)
        steps (Optional[list[str]]): Ordered list of cooking instructions
        servings (Optional[int]): Number of servings the recipe yields (minimum 1)
        serving_size (Optional[float]): Size of each serving (non-negative)
        rating_avg (Optional[float]): Average user rating from 0 to 5 stars
        rating_count (Optional[int]): Total number of user ratings (non-negative)
        similarity (float): Similarity score to the search query from 0 to 1 (higher is more similar)

    Note:
        The similarity field is required and represents how well this recipe matches
        the original search query, making it useful for ranking search results.
    """

    id: int = Field(..., ge=0, description="Recipe ID")
    name: str = Field(..., min_length=1, description="Recipe name")
    description: Optional[str] = Field(None, description="Recipe description")
    tags: Optional[list[str]] = Field(None, description="Recipe tags")
    minutes: Optional[int] = Field(None, ge=0, description="Cooking time in minutes")
    nutrition: Optional[Dict[str, float]] = Field(
        None, description="Nutritional information"
    )
    score_health: Optional[float] = Field(
        None, ge=0, le=1, description="Health score (0-1)"
    )
    n_ingredients: Optional[int] = Field(
        None, ge=0, description="Number of ingredients"
    )
    ingredients: Optional[list[str]] = Field(None, description="List of ingredients")
    n_steps: Optional[int] = Field(None, ge=0, description="Number of steps")
    steps: Optional[list[str]] = Field(None, description="Cooking steps")
    servings: Optional[int] = Field(None, ge=1, description="Number of servings")
    serving_size: Optional[float] = Field(None, ge=0, description="Serving size")
    rating_avg: Optional[float] = Field(None, ge=0, le=5, description="Average rating")
    rating_count: Optional[int] = Field(None, ge=0, description="Number of ratings")
    similarity: float = Field(..., ge=0, le=1, description="Similarity score to query")


class SearchResponse(BaseModel):
    """
    Response model for search operations containing results and metadata.

    This class represents the complete response from a search operation, including
    the actual search results, query information, and performance metrics.

    Attributes:
        results (list[SearchResult]): A list of SearchResult objects representing
            the items found matching the search criteria.
        query (str): The original search query string that was executed.
        total_found (int): The total number of results found for the query.
            Must be non-negative.
        execution_time_ms (float): The time taken to execute the search operation
            in milliseconds. Must be non-negative.

    Example:
        >>> response = SearchResponse(
        ...     results=[result1, result2],
        ...     query="nutrition facts",
        ...     total_found=2,
        ...     execution_time_ms=45.2
        ... )
    """

    results: list[SearchResult] = Field(..., description="List of search results")
    query: str = Field(..., min_length=1, description="Original search query")
    total_found: int = Field(..., ge=0, description="Total number of results found")
    execution_time_ms: float = Field(
        ..., ge=0, description="Time taken to execute the search (in milliseconds)"
    )
