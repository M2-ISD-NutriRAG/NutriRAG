from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
from shared.snowflake.client import SnowflakeClient
from shared.snowflake.tables.recipes_sample_table import RecipesSampleTable
from shared.snowflake.tables.recipes_final_table import RecipesFullTable
from app.models.recipe import Recipe, RecipeListResponse, NutritionDetailed


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

def v(x):
    return -1 if x is None else x
    
@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    # Get a single recipe by ID
    # Returns enriched recipe with:
    # - Parsed ingredients
    # - Health score    
    client = SnowflakeClient()
    result = client.execute(f"""
        SELECT *
        FROM {RecipesFullTable.get_full_table_name()}
        WHERE id = {recipe_id}
     """, fetch="all")
    if len(result) > 0:
        row = result[0]

        nutrition = NutritionDetailed(
            calories=v(row[20]),
            protein_g=v(row[21]),
            fat_g=v(row[23]),
            saturated_fat_g=v(row[22]),
            carbs_g=v(row[24]),
            fiber_g=v(row[25]),
            sugar_g=v(row[26]),
            sodium_mg=v(row[27]),
            calcium_mg=v(row[28]),
            iron_mg=v(row[29]),
            magnesium_mg=v(row[32]),
            potassium_mg=v(row[30]),
            vitamin_c_mg=v(row[31]),
        )
    
        
        recipe = Recipe(
            id=row[1],
            name=row[0],
            description=row[9],
            minutes=row[2],
            n_steps=row[7],
            n_ingredients=row[11],
            tags=parse_list_string(row[5]),
            ingredients_raw=parse_list_string(row[10]),
            ingredients_parsed=None, 
            steps=parse_list_string(row[8]),
            nutrition_original=parse_list_string(row[6]),
            nutrition_detailed=nutrition,
            score_health=row[19],
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
    
    client = SnowflakeClient()
    result = client.execute(f"""
        SELECT *
        FROM {RecipesFullTable.get_full_table_name()}
        WHERE id = {recipe_id}
     """, fetch="all")
    if len(result) > 0:
        row = result[0]

        nutrition = NutritionDetailed(
            calories=v(row[20]),
            protein_g=v(row[21]),
            fat_g=v(row[23]),
            saturated_fat_g=v(row[22]),
            carbs_g=v(row[24]),
            fiber_g=v(row[25]),
            sugar_g=v(row[26]),
            sodium_mg=v(row[27]),
            calcium_mg=v(row[28]),
            iron_mg=v(row[29]),
            magnesium_mg=v(row[32]),
            potassium_mg=v(row[30]),
            vitamin_c_mg=v(row[31]),
        )
    else:
        nutrition = NutritionDetailed(
            calories = -1,
            protein_g = -1,
            fat_g = -1,
            saturated_fat_g = -1,
            carbs_g = -1,
            fiber_g = -1,
            sugar_g = -1,
            sodium_mg = -1,
        
            calcium_mg = -1,
            iron_mg = -1,
            magnesium_mg = -1,
            potassium_mg = -1,
            vitamin_c_mg = -1
        )
    return nutrition

        


@router.get("/random")
async def get_random_recipes(count: int = Query(5, ge=1, le=20)):
    # Obtenir des recettes aléatoires pour l'exploration
    # TODO: Équipe 1 - Échantillonner des recettes aléatoires
    client = SnowflakeClient()
    # Ensure count is strictly an integer and within bounds before interpolation
    safe_count = int(count)
    results = client.execute(f"""
        SELECT *
        FROM {RecipesSampleTable.get_full_table_name()}
        SAMPLE ({safe_count} rows)
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



