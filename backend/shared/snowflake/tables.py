"""Snowflake table definitions and column enums."""

from enum import Enum
from typing import List


class Table:
    """Base class for table enums with common functionality."""

    @classmethod
    def get_columns(cls) -> type[Enum]:
        """Returns the Columns enum class.

        Raises:
            AttributeError: If the subclass doesn't define a Columns attribute.
        """
        if not hasattr(cls, "Columns"):
            raise AttributeError(
                f"{cls.__name__} must define a 'Columns' inner class (Enum) "
                "to use the get_columns() method."
            )
        return cls.Columns


class RecipesSampleTable(Table):
    NAME = "RECIPES_SAMPLE"

    class Columns(str, Enum):
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
    def get_columns_to_concat_for_embedding() -> List["RecipesSampleTable.Columns"]:
        return [
            RecipesSampleTable.Columns.NAME,
            RecipesSampleTable.Columns.DESCRIPTION,
            RecipesSampleTable.Columns.INGREDIENTS,
            RecipesSampleTable.Columns.STEPS,
            RecipesSampleTable.Columns.TAGS,
        ]


class RecipesUnifiedEmbeddingsTable(Table):
    NAME = "RECIPES_UNIFIED_EMBEDDINGS"

    class Columns(str, Enum):
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
