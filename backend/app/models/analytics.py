from typing import List, Optional
from pydantic import BaseModel


class Cluster(BaseModel):
    # Ingredient or recipe cluster
    cluster_id: int
    label: str
    size: int
    examples: List[str]
    centroid: Optional[List[float]] = None


class ClusterResponse(BaseModel):
    # Clustering results
    clusters: List[Cluster]
    total_clusters: int
    algorithm: str
    feature_type: str


class KPI(BaseModel):
    # Single KPI metric
    name: str
    value: float
    unit: str
    description: str
    team: Optional[str] = None


class TopIngredient(BaseModel):
    name: str
    count: int


class BiggestWin(BaseModel):
    original_name: str
    transformed_name: str
    health_score_delta: float


class RecipeRanking(BaseModel):
    name: str
    health_score: float


class TopFilter(BaseModel):
    name: str
    count: int


class TopTag(BaseModel):
    name: str
    count: int


class SearchNutritionStats(BaseModel):
    avg_calories: float
    avg_protein: float
    avg_fat: float
    avg_carbs: float
    avg_sugar: float
    avg_fiber: float
    avg_sodium: float


class KPIResponse(BaseModel):
    total_searches: int
    total_transformations: int
    conversion_rate: float
    total_calories_saved: float
    total_protein_gained: float
    avg_health_score_gain: float
    search_nutrition_avg: (
        SearchNutritionStats  # Moyenne nutritionnelle des recherches
    )
    top_filters: List[TopFilter]  # Top filtres utilisés
    top_tags: List[TopTag]  # Top tags des recettes vues
    ingredient_diversity_index: int
    top_ingredients: List[TopIngredient]
    biggest_optimization: Optional[BiggestWin]
    top_5_healthy_recipes: List[RecipeRanking]
    top_5_unhealthy_recipes: List[RecipeRanking]
    avg_recipe_time: float
    avg_time_saved: float


class TransformationSummary(BaseModel):
    original_name: str
    transformed_name: str
    delta_calories: float
    delta_protein: float
    delta_fat: float
    delta_carbs: float
    delta_fiber: float
    delta_sugar: float
    delta_sodium: float
    delta_health_score: float


class ConversationStatsResponse(BaseModel):
    total_messages: int
    total_transformations: int
    transformations_list: List[TransformationSummary]
