"""Snowflake table definitions."""

from shared.snowflake.tables.recipes_sample_50k_table import (
    RecipesSample50kTable,
    Recipes50kEmbeddingsTable,
)
from shared.snowflake.tables.table import Table

__all__ = [
    "Table",
    "RecipesSample50kTable",
    "Recipes50kEmbeddingsTable",
]
