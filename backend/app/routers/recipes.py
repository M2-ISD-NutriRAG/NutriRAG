from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.models.recipe import Recipe, RecipeListResponse
from app.services.snowflake_client import SnowflakeClient

router = APIRouter()


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    # Get a single recipe by ID
    # Returns enriched recipe with:
    # - Parsed ingredients
    # - Detailed nutrition
    # - Health score    
    # TODO: Équipe 1 - Implémentation de la requête Snowflake
    session = get_snowflake_session()
    result = session.sql(f"""
        SELECT *
        FROM NutriRAG_Project.DEV_SAMPLE.RECIPES_SAMPLE
        WHERE id = {recipe_id}
     """).collect()
    row = result[0]

    recipe = Recipe(
        id=row["ID"],
        name=row["NAME"],
        description=row["DESCRIPTION"],
        minutes=row["MINUTES"],
        n_steps=row["N_STEPS"],
        n_ingredients=row["N_INGREDIENTS"],
        tags=row["TAGS"],
        ingredients_raw=row["INGREDIENTS"],
        ingredients_parsed=None,  # pas encore calculé
        steps=row["STEPS"],
        nutrition_original=row["NUTRITION"],
        nutrition_detailed=None,  # pas encore calculé
        score_health=None,
        rating_avg=None,
        rating_count=None
    )

    return recipe
    # Mock response for now
    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Requête Snowflake ENRICHED.recipes_detailed"
    )


@router.get("/", response_model=RecipeListResponse)
async def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    tag: Optional[str] = None,
    min_rating: Optional[float] = None
):
    # List recipes with pagination and filters
    # TODO: Équipe 1 - Implémentation de la requête Snowflake avec filtres
    
    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Requête des recettes avec filtres"
    )


@router.get("/{recipe_id}/nutrition")
async def get_recipe_nutrition(recipe_id: int):
    # Obtenir la décomposition nutritionnelle détaillée pour une recette
    # TODO: Équipe 1 - Retourner la décomposition nutritionnelle détaillée par ingrédient

    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Retourner la décomposition nutritionnelle détaillée par ingrédient"
    )


@router.get("/random")
async def get_random_recipes(count: int = Query(5, ge=1, le=20)):
    # Obtenir des recettes aléatoires pour l'exploration
    # TODO: Équipe 1 - Échantillonner des recettes aléatoires
    results = session.sql(f"""
        SELECT *
        FROM NutriRAG_Project.DEV_SAMPLE.RECIPES_SAMPLE
        SAMPLE ({count} rows)
    """).collect()

    recipes = []
    for row in results:
        recipes.append({
            "id": row["ID"],
            "name": row["NAME"],
            "description": row["DESCRIPTION"],
            "minutes": row["MINUTES"],
            "n_steps": row["N_STEPS"],
            "n_ingredients": row["N_INGREDIENTS"],
            "tags": row["TAGS"],
            "ingredients_raw": row["INGREDIENTS"],
            "ingredients_parsed": None,
            "steps": row["STEPS"],
            "nutrition_original": row["NUTRITION"],
            "nutrition_detailed": None,
            "score_health": None,
            "rating_avg": None,
            "rating_count": None
        })

    return recipes

    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implémentation nécessaire - Échantillonnage des recettes aléatoires"
    )

