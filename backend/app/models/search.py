from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    # Nutrition filters for search
    protein_min: Optional[float] = None
    protein_max: Optional[float] = None
    carbs_min: Optional[float] = None
    carbs_max: Optional[float] = None
    calories_min: Optional[float] = None
    calories_max: Optional[float] = None
    fat_max: Optional[float] = None
    fiber_min: Optional[float] = None
    sodium_max: Optional[float] = None
    
    # Tags filters
    tags_include: Optional[list[str]] = None
    tags_exclude: Optional[list[str]] = None
    
    # Score filters
    score_health_min: Optional[float] = None
    rating_min: Optional[float] = None


class SearchRequest(BaseModel):
    # Search request body
    query: str = Field(..., description="Natural language search query")
    filters: Optional[SearchFilters] = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    # Single search result
    id: int
    name: str
    description: Optional[str] = None
    similarity: float
    nutrition: Optional[Dict[str, float]] = None
    score_health: Optional[float] = None
    rating_avg: Optional[float] = None
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    # Search response
    results: list[SearchResult]
    query: str
    total_found: int
    execution_time_ms: float

