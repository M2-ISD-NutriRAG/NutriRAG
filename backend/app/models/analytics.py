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


class KPIResponse(BaseModel):
    # Métriques Générales
    total_searches: int
    total_transformations: int
    conversion_rate: float
    # Métriques Nutritionnelles Cumulées
    total_calories_saved: float
    total_protein_gained: float  # Nouveau
    avg_health_score_gain: float
    # Métriques Ingrédients & Diversité
    ingredient_diversity_index: (
        int  # Nouveau (Nombre d'ingrédients uniques explorés)
    )
    top_ingredients: List[TopIngredient]  # Nouveau
    # Métriques "Fun" / Gamification
    biggest_optimization: Optional[BiggestWin]  # Nouveau
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
