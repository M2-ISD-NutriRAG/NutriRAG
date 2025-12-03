"""Snowflake table definitions."""

from shared.snowflake.tables.recipes_sample_table import (
    RecipesSampleTable,
    RecipesUnifiedEmbeddingsTable,
)
from shared.snowflake.tables.table import Table

__all__ = [
    "Table",
    "RecipesSampleTable",
    "RecipesUnifiedEmbeddingsTable",
]
