from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import json
from shared.snowflake.client import SnowflakeClient
from shared.snowflake.tables.recipes_sample_50k_table import (
    RecipesSample50kTable,
)
from app.models.recipe import Recipe, RecipeListResponse, NutritionDetailed


router = APIRouter()


def parse_list_string(value: str) -> Optional[List]:
    """
    Parse a string representation of a list into an actual Python list.
    Handles formats like:
    '[\n  "tag1",\n  "tag2"\n]'
    '[\n  6.9e+01,\n  3\n]'
    """
    if value is None or value == "":
        return None

    value = value.strip()

    # Try JSON parsing first
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Manual parsing for malformed JSON
    if value.startswith("[") and value.endswith("]"):
        content = value[1:-1].strip()

        if not content:
            return []

        parts = [p.strip().strip('"').strip("'") for p in content.split(",")]

        result = []
        for p in parts:
            if not p:
                continue
            try:
                # Try to parse as float first
                result.append(float(p))
            except ValueError:
                result.append(p)
        return result

    # Single value fallback
    return [value]


def safe_int(value, default: int = -1) -> int:
    """Safely convert value to int, return default if None or invalid."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """Safely convert value to float, return default if None or invalid."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default: str = "") -> str:
    """Safely convert value to string, return default if None."""
    if value is None:
        return default
    return str(value)


def parse_nutrition_from_row(row) -> Optional[NutritionDetailed]:
    """Parse nutrition data from database row."""
    try:
        return NutritionDetailed(
            calories=safe_float(row[20]),
            protein_g=safe_float(row[21]),
            fat_g=safe_float(row[23]),
            saturated_fat_g=safe_float(row[22]),
            carbs_g=safe_float(row[24]),
            fiber_g=safe_float(row[25]),
            sugar_g=safe_float(row[26]),
            sodium_mg=safe_float(row[27]),
            calcium_mg=safe_float(row[28]),
            iron_mg=safe_float(row[29]),
            magnesium_mg=safe_float(row[32]),
            potassium_mg=safe_float(row[30]),
            vitamin_c_mg=safe_float(row[31]),
        )
    except Exception:
        return None


def parse_recipe_from_row(row) -> Recipe:
    """Parse a complete Recipe object from a database row."""
    # Parse tags, ingredients, and steps
    tags = parse_list_string(row[5]) or []
    ingredients_raw = parse_list_string(row[10]) or []
    steps = parse_list_string(row[8]) or []
    nutrition_original = parse_list_string(row[6]) or []

    # Ensure they are lists of strings
    tags = [safe_str(t) for t in tags]
    ingredients_raw = [safe_str(i) for i in ingredients_raw]
    steps = [safe_str(s) for s in steps]

    # Parse nutrition
    nutrition_detailed = parse_nutrition_from_row(row)

    return Recipe(
        id=safe_int(row[1], -1),
        name=safe_str(row[0], "Unknown Recipe"),
        description=safe_str(row[9]),
        minutes=safe_int(row[2]),
        n_steps=safe_int(row[7]),
        n_ingredients=safe_int(row[11]),
        tags=tags,
        ingredients_raw=ingredients_raw,
        ingredients_parsed=None,
        steps=steps,
        nutrition_original=nutrition_original,
        nutrition_detailed=nutrition_detailed,
        score_health=safe_float(row[19]),
        rating_avg=None,
        rating_count=None,
    )


@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int):
    """
    Get a single recipe by ID.
    Returns enriched recipe with parsed ingredients and health score.
    """
    client = SnowflakeClient()

    result = client.execute(
        f"""
        SELECT *
        FROM {RecipesSample50kTable.get_full_table_name()}
        WHERE id = {recipe_id}
        """,
        fetch="all",
    )

    if not result:
        raise HTTPException(
            status_code=404, detail=f"Recipe with id {recipe_id} not found"
        )

    return parse_recipe_from_row(result[0])


@router.get("/{recipe_id}/nutrition", response_model=NutritionDetailed)
async def get_recipe_nutrition(recipe_id: int):
    """
    Get detailed nutritional breakdown for a recipe.
    """
    client = SnowflakeClient()

    result = client.execute(
        f"""
        SELECT *
        FROM {RecipesSample50kTable.get_full_table_name()}
        WHERE id = {recipe_id}
        """,
        fetch="all",
    )

    if not result:
        raise HTTPException(
            status_code=404, detail=f"Recipe with id {recipe_id} not found"
        )

    nutrition = parse_nutrition_from_row(result[0])

    if nutrition is None:
        raise HTTPException(
            status_code=404,
            detail=f"Nutrition data not available for recipe {recipe_id}",
        )

    return nutrition


@router.get("/random", response_model=List[Recipe])
async def get_random_recipes(count: int = Query(5, ge=1, le=20)):
    """
    Get random recipes for exploration.
    """
    client = SnowflakeClient()

    # Validate count
    safe_count = max(1, min(int(count), 20))

    results = client.execute(
        f"""
        SELECT *
        FROM {RecipesSample50kTable.get_full_table_name()}
        SAMPLE ({safe_count} ROWS)
        """,
        fetch="all",
    )

    recipes = []
    for row in results:
        try:
            recipe = parse_recipe_from_row(row)
            recipes.append(recipe)
        except Exception:
            continue

    return recipes


@router.get("/", response_model=RecipeListResponse)
async def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    tag: Optional[str] = None,
    min_rating: Optional[float] = None,
):
    """
    List recipes with pagination and filters.
    TODO: Équipe 1 - Implementation of Snowflake query with filters
    """
    raise HTTPException(
        status_code=501,
        detail="Équipe 1: Implementation required - Recipe query with filters",
    )
