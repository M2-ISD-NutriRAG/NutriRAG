# Snowflake Tables

## Available Tables

### RecipesSampleTable

Source table with raw recipe data.

**Key columns:** `ID`, `NAME`, `DESCRIPTION`, `INGREDIENTS`, `STEPS`, `TAGS`, `NUTRITION`

```python
from shared.snowflake.tables import RecipesSampleTable

# Use column enums
RecipesSampleTable.Columns.NAME  # "NAME"
RecipesSampleTable.NAME           # "RECIPES_SAMPLE"
```

### RecipesUnifiedEmbeddingsTable

Target table with embeddings for semantic search.

**Additional columns:** `CONCATENATED_TEXT_FOR_RAG`, `EMBEDDING`, expanded nutrition (`CALORIES`, `PROTEIN`, `CARBS`, etc.)

```python
from shared.snowflake.tables import RecipesUnifiedEmbeddingsTable

RecipesUnifiedEmbeddingsTable.Columns.EMBEDDING  # "EMBEDDING"
```

## Adding New Tables

1. Edit [tables.py](tables.py) - create new class extending `Table`
2. Define `NAME` and `Columns` enum
3. Import and use: `from shared.snowflake.tables import MyNewTable`
