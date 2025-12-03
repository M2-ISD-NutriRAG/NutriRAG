from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
from shared.snowflake.client import SnowflakeClient
from shared.snowflake.tables.recipes_sample_table import RecipesSampleTable
from app.models.recipe import Recipe, RecipeListResponse

router = APIRouter()



def parse_list_string(value: str):
    """
    Transforme un string comme :
    '[\n  "tag1",\n  "tag2"\n]'
    ou
    '[\n  6.9e+01,\n  3\n]'
    en vraie liste Python.
    """
    if value is None:
        return None

    value = value.strip()

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    if value.startswith("[") and value.endswith("]"):
        content = value[1:-1].strip()

        parts = [p.strip().strip('"').strip("'") for p in content.split(",")]

        out = []
        for p in parts:
            try:
                out.append(float(p))
            except:
                out.append(p)
        return out

    return [value]


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    # Get a single recipe by ID
    # Returns enriched recipe with:
    # - Parsed ingredients
    # - Health score    
    # TODO: Équipe 1 - Implémentation de la requête Snowflake
    client = SnowflakeClient()
    result = client.execute(f"""
        SELECT *
        FROM {RecipesSampleTable.get_full_table_name()}
        WHERE id = {recipe_id}
     """, fetch="all")
    if len(result) > 0:
        row = result[0]
    
        recipe = Recipe(
            id=row[1],
            name=row[0],
            description=row[9],
            minutes=row[2],
            n_steps=row[7],
            n_ingredients=row[11],
            tags=parse_list_string(row[5]),
            ingredients_raw=parse_list_string(row[10]),
            ingredients_parsed=None,  # pas encore calculé
            steps=parse_list_string(row[8]),
            nutrition_original=parse_list_string(row[6]),
            nutrition_detailed=None,  # pas encore calculé
            score_health=None,
            rating_avg=None,
            rating_count=None
        )
    else: 
        recipe = Recipe(
            id=-1,
            name="",
            description="",
            minutes=-1,
            n_steps=-1,
            n_ingredients=-1,
            tags=[],
            ingredients_raw=[],
            ingredients_parsed=None,  # pas encore calculé
            steps=[],
            nutrition_original=[],
            nutrition_detailed=None,  # pas encore calculé
            score_health=None,
            rating_avg=None,
            rating_count=None)

    return recipe



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
    client = SnowflakeClient()
    results = client.execute(f"""
        SELECT *
        FROM {RecipesSampleTable.get_full_table_name()}
        SAMPLE ({count} rows)
    """, fetch="all")

    recipes = []
    for row in results:
        recipes.append(Recipe(
        id=row[1],
        name=row[0],
        description=row[9],
        minutes=row[2],
        n_steps=row[7],
        n_ingredients=row[11],
        tags=parse_list_string(row[5]),
        ingredients_raw=parse_list_string(row[10]),
        ingredients_parsed=None,  # pas encore calculé
        steps=parse_list_string(row[8]),
        nutrition_original=parse_list_string(row[6]),
        nutrition_detailed=None,  # pas encore calculé
        score_health=None,
        rating_avg=None,
        rating_count=None
    ))


    return recipes



