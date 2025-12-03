"""Snowflake table definitions for RECIPES_SAMPLE and RECIPES_UNIFIED_EMBEDDINGS tables."""

from typing import List

from shared.snowflake.tables.table import define_snowflake_table, Table


@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="DEV_SAMPLE",
    TABLE_NAME="RECIPES_SAMPLE",
)
class RecipesSampleTable(Table):
    NAME = "NAME"
    ID = "ID"
    MINUTES = "MINUTES"
    CONTRIBUTOR_ID = "CONTRIBUTOR_ID"
    SUBMITTED = "SUBMITTED"
    TAGS = "TAGS"
    NUTRITION = "NUTRITION"
    N_STEPS = "N_STEPS"
    STEPS = "STEPS"
    DESCRIPTION = "DESCRIPTION"
    INGREDIENTS = "INGREDIENTS"
    N_INGREDIENTS = "N_INGREDIENTS"
    HAS_IMAGE = "HAS_IMAGE"
    IMAGE_URL = "IMAGE_URL"
    INGREDIENTS_RAW_STR = "INGREDIENTS_RAW_STR"
    SERVING_SIZE = "SERVING_SIZE"
    SERVINGS = "SERVINGS"
    SEARCH_TERMS = "SEARCH_TERMS"
    FILTERS = "FILTERS"

    @staticmethod
    def get_columns_to_concat_for_embedding() -> List["RecipesSampleTable"]:
        return [
            RecipesSampleTable.NAME,
            RecipesSampleTable.DESCRIPTION,
            RecipesSampleTable.INGREDIENTS,
            RecipesSampleTable.STEPS,
            RecipesSampleTable.TAGS,
        ]


@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="DEV_SAMPLE",
    TABLE_NAME="RECIPES_UNIFIED_EMBEDDINGS",
)
class RecipesUnifiedEmbeddingsTable(Table):
    # Common columns with RecipesSampleTable
    ID = "ID"
    NAME = "NAME"
    MINUTES = "MINUTES"
    CONTRIBUTOR_ID = "CONTRIBUTOR_ID"
    SUBMITTED = "SUBMITTED"
    TAGS = "TAGS"
    NUTRITION = "NUTRITION"
    N_STEPS = "N_STEPS"
    STEPS = "STEPS"
    DESCRIPTION = "DESCRIPTION"
    INGREDIENTS = "INGREDIENTS"
    N_INGREDIENTS = "N_INGREDIENTS"
    HAS_IMAGE = "HAS_IMAGE"
    IMAGE_URL = "IMAGE_URL"
    INGREDIENTS_RAW_STR = "INGREDIENTS_RAW_STR"
    SERVING_SIZE = "SERVING_SIZE"
    SERVINGS = "SERVINGS"
    SEARCH_TERMS = "SEARCH_TERMS"
    FILTERS = "FILTERS"
    # Nutrition columns (expanded)
    CALORIES = "CALORIES"
    TOTAL_FAT = "TOTAL_FAT"
    SUGAR = "SUGAR"
    SODIUM = "SODIUM"
    PROTEIN = "PROTEIN"
    SATURATED_FAT = "SATURATED_FAT"
    CARBS = "CARBS"
    # Embedding columns
    CONCATENATED_TEXT_FOR_RAG = "CONCATENATED_TEXT_FOR_RAG"
    EMBEDDING = "EMBEDDING"
