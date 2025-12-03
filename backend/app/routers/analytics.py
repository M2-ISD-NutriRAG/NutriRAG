from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.models.analytics import ClusterResponse, KPIResponse

router = APIRouter()


@router.get("/clusters/ingredients", response_model=ClusterResponse)
async def get_ingredient_clusters(algorithm: Optional[str] = "kmeans"):
    # Obtenir les résultats du regroupement (clustering) des ingrédients
    # Retourne des clusters avec des étiquettes et des exemples
    # TODO: Équipe 4 - Retourner les clusters d'ingrédients de Snowflake
    
    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Requête des clusters d'ingrédients"
    )


@router.get("/clusters/recipes", response_model=ClusterResponse)
async def get_recipe_clusters():
    # Obtenir les résultats du regroupement (clustering) des recettes (types de cuisine, catégories de plats)    
    # TODO: Équipe 4 - Retourner les clusters de recettes

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Requête des clusters de recettes"
    )


@router.get("/kpi", response_model=KPIResponse)
async def get_kpis(team: Optional[str] = None):
    # Obtenir tous les KPIs ou filtrer par équipe
    # Available KPIs:
    # - matching_rate: % ingredients matched with cleaned_ingredients (Équipe 1)
    # - precision@5: Top 5 results relevance (Équipe 2)
    # - health_improvement: Delta score health transformations (Équipe 3)
    # - latency_avg: Average response time (Équipe 5)
    # - coverage: % recipes with complete nutrition (Équipe 1)
    # TODO: Équipe 4 - Calculer et retourner les KPIs

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Calculer les KPIs à partir des données"
    )


@router.get("/distributions/{metric}")
async def get_distribution(metric: str):
    # Obtenir la distribution d'une mesure nutritionnelle sur les recettes
    # Mesures: calories, protein, carbs, fat, score_health
    # TODO: Équipe 4 - Retourner les données de l'histogramme/distribution

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Calculer les distributions"
    )


@router.get("/correlations")
async def get_correlations():
    # Obtenir la matrice de corrélation entre les mesures nutritionnelles et les évaluations
    # TODO: Équipe 4 - Calculer les corrélations

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Analyse de corrélation"
    )

