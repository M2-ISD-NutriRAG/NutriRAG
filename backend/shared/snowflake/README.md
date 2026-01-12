# Snowflake Tables

## Available Tables

### RecipesSample50kTable

Source table with raw recipe data.

**Key columns:** `ID`, `NAME`, `DESCRIPTION`, `INGREDIENTS`, `STEPS`, `TAGS`, `NUTRITION`, etc.

```python
from shared.snowflake.tables import RecipesSample50kTable

# Use column enums
RecipesSample50kTable.NAME  # "NAME"
```

### Recipes50kEmbeddingsTable

Target table with embeddings for semantic search.

**Additional columns:** `CONCATENATED_TEXT_FOR_RAG`, `EMBEDDING`, expanded nutrition (`CALORIES`, `PROTEIN`, `CARBS`, etc.)

```python
from shared.snowflake.tables import Recipes50kEmbeddingsTable

Recipes50kEmbeddingsTable.EMBEDDING  # "EMBEDDING"
```

## Adding New Tables

1. Create a new file in [tables/](tables/) directory (e.g., `my_new_table.py`)
2. Create a new class extending `Table` and decorate it with `@define_snowflake_table`
3. Define column names as class attributes
4. Add the new table to [tables/**init**.py](tables/__init__.py) exports
5. Import and use: `from shared.snowflake.tables import MyNewTable`

Example:

```python
from shared.snowflake.tables.table import define_snowflake_table, Table

@define_snowflake_table(
    SNOWFLAKE_DATABASE="NUTRIRAG_PROJECT",
    SCHEMA_NAME="DEV_SAMPLE",
    TABLE_NAME="MY_NEW_TABLE",
)
class MyNewTable(Table):
    ID = "ID"
    NAME = "NAME"
    # ... other columns
```
