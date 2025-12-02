from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from shared.snowflake.client import SnowflakeClient

from app.models.recipe import Recipe, RecipeListResponse

router = APIRouter()


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    # Get a single recipe by ID
    # Returns enriched recipe with:
    # - Parsed ingredients
    # - Detailed nutrition
    # - Health score

    # TODO: Équipe 1 - Implémentation de la requête Snowflake
    # client = SnowflakeClient()
    # result = client.execute(f"""
    #     SELECT *
    #     FROM NutriRAG_Project.ENRICHED.recipes_detailed
    #     WHERE id = {recipe_id}
    # """, fetch='all')

    # Mock response for now
    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Requête Snowflake ENRICHED.recipes_detailed",
    )


@router.get("/", response_model=RecipeListResponse)
async def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    tag: Optional[str] = None,
    min_rating: Optional[float] = None,
):
    # List recipes with pagination and filters
    # TODO: Équipe 1 - Implémentation de la requête Snowflake avec filtres

    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Requête des recettes avec filtres",
    )


@router.get("/{recipe_id}/nutrition")
async def get_recipe_nutrition(recipe_id: int):
    # Obtenir la décomposition nutritionnelle détaillée pour une recette
    # TODO: Équipe 1 - Retourner la décomposition nutritionnelle détaillée par ingrédient

    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Retourner la décomposition nutritionnelle détaillée par ingrédient",
    )


@router.get("/random")
async def get_random_recipes(count: int = Query(5, ge=1, le=20)):
    # Obtenir des recettes aléatoires pour l'exploration
    # TODO: Équipe 1 - Échantillonner des recettes aléatoires

    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Échantillonnage des recettes aléatoires",
    )
