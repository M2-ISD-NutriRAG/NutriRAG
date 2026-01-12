
# NutriRAG Search Services - Complete Guide

Comprehensive documentation for using NutriRAG's three search services.

## Table of Contents
1. [What You Need to Know](#what-you-need-to-know)
2. [Quick Start](#quick-start)
3. [Vector Search - "Semantic" Search](#vector-search)
4. [BM25 Search - "Keyword" Search](#bm25-search)
5. [Hybrid Search - "Best of Both"](#hybrid-search)
6. [Agent Tool - Search Similar Recipes Tool](#agent-tool---search-similar-recipes-tool)
7. [Filtering Your Results](#filtering-your-results)
8. [BM25 Index Maintenance](#index-maintenance)
9. [Embedding Updates](#updating-embeddings)
10. [Quick Reference](#quick-reference)

---

## What You Need to Know


NutriRAG provides three search engines for recipe retrieval:

### Vector Search
- Interprets the intent behind queries, not just keywords
- Best for: conceptual queries (e.g., "healthy desserts", "quick meals")
- Example: Searching "light and refreshing" can return lemon desserts even if "lemon" is not mentioned

### BM25 Search
- Finds recipes based on exact keyword matches
- Best for: specific recipe names or ingredients (e.g., "chocolate cake", "pasta recipes")
- Example: Searching "chocolate chip cookies" returns recipes with those exact words

### Hybrid Search
- Combines both semantic and keyword-based search with adjustable weights using RRF (ranked retrieval fusion).
- Best for: general-purpose queries where both meaning and keywords are important
- Example: Searching "Italian pasta" leverages both understanding and keyword matching

---

## Quick Start

### One-Time Setup (First time only)

```python
# Python version
from shared.snowflake.client import SnowflakeClient
from app.services.vector_search_service import VectorSearchService
from app.services.bm25_service import BM25Service
from app.services.search_service import SearchService

# Connect to Snowflake
client = SnowflakeClient()

# Initialize with setup=True to create everything you need
search_service = SearchService(client, setup=True)

print("All procedures and tables created.")
```

### Regular Usage (After setup)

```python
from shared.snowflake.client import SnowflakeClient
from app.services.vector_search_service import VectorSearchService

client = SnowflakeClient()
service = VectorSearchService(client)  # No setup=True needed

# Start searching!
results = service.search_semantic(query="chocolate cake")
```

---

## Vector Search


### Overview
Vector Search interprets the semantic meaning of queries and retrieves recipes based on conceptual similarity. This is particularly effective for queries that are descriptive or abstract.

### Python Usage

```python
results = vector_service.search_semantic(
    query="healthy breakfast",
    top_k=5
)

for recipe in results:
    score = recipe['COSINE_SIMILARITY_SCORE']
    print(f"{recipe['NAME']} - Score: {score:.2f}")
```


### Direct Snowflake SQL

```sql
-- Snowflake SQL version
-- Basic search
CALL VECTORS.search_semantic(
    'healthy breakfast',                    -- Your query
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS',      -- Which recipes to search
    5,                                      -- How many results
    NULL                                    -- No filters
);

-- With time filter
CALL VECTORS.search_semantic(
    'quick vegetarian meal',
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS',
    10,
    'MINUTES <= 30'
);
```

### Parameters Explained

| Parameter | What It Is | Example |
|-----------|-----------|---------|
| `query` | What you're looking for | `"chocolate cake"` |
| `top_k` | How many results | `5` to `20` |
| `embeddings_table` | Which recipes to search | `"VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS"` |
| `filter_conditions` | Extra filters (optional) | `"MINUTES <= 30"` |)

---

## BM25 Search


### Overview
BM25 Search retrieves recipes based on keyword frequency and importance, similar to traditional search engines. It is most effective for precise or ingredient-based queries.

### Step 1: Build An Index (First time per table)

```python
# Python version
result = bm25_service.build_index(
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    text_columns=["NAME", "DESCRIPTION", "INGREDIENTS"],
    id_column="ID",
    field_weights={
        "NAME": 3,              # Names are VERY important
        "DESCRIPTION": 2,       # Descriptions are important
        "INGREDIENTS": 1        # Less important
    }
)

print(f"Index created: {result['index_table']}")
```

### Direct Snowflake SQL (Building Index)

```sql
-- Snowflake SQL version
-- Create BM25 index
-- Note: This is typically done via Python, but can be called directly
CALL VECTORS.build_bm25_index(
    'ENRICHED.RECIPES_SAMPLE_50K',                 -- Source table
    ['NAME', 'DESCRIPTION', 'INGREDIENTS'],        -- Columns to index
    'ID',                                          -- ID column
    {'NAME': 3, 'DESCRIPTION': 2, 'INGREDIENTS': 1} -- Field weights
);
```

### Step 2: Search Using The Index

```python
# Python version
results = bm25_service.search(
    query="chocolate cake",
    index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    top_k=10
)

for recipe in results:
    print(f"{recipe['NAME']} - Score: {recipe['BM25_SCORE']:.2f}")
```

### Parameters Explained (BM25 Search)

| Parameter | What It Is | Example |
|-----------|-----------|----------|
| `query` | Search keywords | `"chocolate cake"` |
| `index_table` | BM25 index table name | `"VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX"` |
| `source_table` | Original recipe table | `"ENRICHED.RECIPES_SAMPLE_50K"` |
| `top_k` | Number of results to return | `5` to `20` |
| `filter_conditions` | SQL WHERE clause for filtering (optional) | `"MINUTES <= 30"` |

### Direct Snowflake SQL (Search)

```sql
-- Snowflake SQL version
-- Basic search
CALL VECTORS.search_bm25(
    'chocolate cake',                              -- Query
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',     -- Index table
    'ENRICHED.RECIPES_SAMPLE_50K',                -- Source table
    10,                                           -- Results limit
    NULL                                          -- No filters
);

-- Search with time filter
CALL VECTORS.search_bm25(
    'pasta',
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
    'ENRICHED.RECIPES_SAMPLE_50K',
    10,
    'MINUTES <= 30'
);
```

---

## Hybrid Search

### What It Does
Combines smart understanding + keyword matching with adjustable weights. You decide the balance!

**Formula:**
```
Final Score = (Semantic Match × vector_weight) + (Keyword Match × bm25_weight)
```

### Python Usage

```python
# Python version
results = service.search(
    query="Italian pasta dinner",
    limit=10,
    vector_weight=0.7,     # 70% understanding
    bm25_weight=0.3        # 30% keywords
)

for recipe in results:
    score = recipe['COMBINED_SCORE']
    print(f"{recipe['NAME']} - {score:.0%} match")
```

### Parameters Explained (Hybrid Search)

| Parameter | What It Is | Example |
|-----------|-----------|----------|
| `query` | Search query (can be conceptual or keywords) | `"Italian pasta"` |
| `limit` | Number of results to return | `5` to `20` |
| `filters` | Filter criteria (optional) | `SearchFilters(dietary_filters=["vegetarian"])` |
| `vector_weight` | Weight for semantic similarity (0.0-1.0) | `0.7` |
| `bm25_weight` | Weight for keyword relevance (0.0-1.0) | `0.3` |
| `index_table` | BM25 index table name | `"VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX"` |
| `source_table` | Original recipe table | `"ENRICHED.RECIPES_SAMPLE_50K"` |
| `embeddings_table` | Embeddings table for semantic search | `"VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS"` |

### Direct Snowflake SQL

```sql
-- Snowflake SQL version
-- Default: More semantic, less keyword
CALL VECTORS.SEARCH_SIMILAR_RECIPES(
    'pasta with tomato sauce',                      -- Query
    10,                                             -- Limit
    NULL,                                           -- No filters
    0.7,                                            -- 70% semantic
    0.3,                                            -- 30% keyword
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',       -- BM25 index
    'ENRICHED.RECIPES_SAMPLE_50K',                 -- Source table
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS'               -- Embeddings
);

-- Keyword-focused: More keyword, less semantic
CALL VECTORS.SEARCH_SIMILAR_RECIPES(
    'chocolate chip cookies',
    5,
    NULL,
    0.3,                                            -- 30% semantic
    0.7,                                            -- 70% keyword
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
    'ENRICHED.RECIPES_SAMPLE_50K',
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS'
);

-- With filters (dietary + time)
CALL VECTORS.SEARCH_SIMILAR_RECIPES(
    'vegetarian dinner',
    10,
    '{"dietary_filters": ["vegetarian"], "numeric_filters": [{"name": "minutes", "operator": "<=", "value": 30}]}',
    0.6,
    0.4,
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
    'ENRICHED.RECIPES_SAMPLE_50K',
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS'
);
```

---

## Agent Tool - Search Similar Recipes Tool

### Overview
The `SEARCH_SIMILAR_RECIPES_TOOL` is the primary search interface exposed to AI agents. It internally uses **Hybrid Search** by default, combining both semantic understanding and keyword matching to deliver the best results for a wide variety of queries.

### Snowflake SQL Usage

```sql
-- Snowflake SQL version
CALL SERVICES.SEARCH_SIMILAR_RECIPES_TOOL(
    'user@example.com',                    -- User identifier
    'vegetarian pasta dinner',             -- Search query
    10,                                    -- Number of results
    '{"dietary_filters": ["vegetarian"]}'  -- Optional filters as JSON
);
```

### Parameters Explained (Agent Tool)

| Parameter | What It Is | Example |
|-----------|-----------|---------|
| `user_input` | User identifier making the request | `'user@example.com'` |
| `query_input` | Search query (can be conceptual or keywords) | `'healthy pasta dinner'` |
| `k_input` | Number of results to return | `5` to `20` |
| `filters_input` | Optional filter JSON string | `'{"dietary_filters": ["vegetarian"]}'` or `NULL` |

### Under the Hood
This tool automatically:
- Uses hybrid search with balanced weights (vector_weight: 0.7, bm25_weight: 0.3)
- Searches across semantic embeddings and BM25 index
- Applies any filters provided
- Returns ranked results based on combined scoring

### Response Format
Returns a JSON object with:
- `results`: List of matching recipes
- `query`: The processed query
- `total_found`: Number of results returned
- `execution_time_ms`: Time taken for search
- `status`: Either "success" or "error"

---

## Filtering Your Results

### Available Filters

You can filter by:
1. **Time** (minutes)
2. **Servings**
3. **Dietary tags** (vegetarian, vegan, gluten-free, etc.)
4. **Ingredients** (must have, must NOT have, at least one)

### Python: Using Filters

```python
# Python version
from app.models.search import SearchFilters, NumericFilter

filters = SearchFilters(
    # Time: <= 30 minutes
    numeric_filters=[
        NumericFilter(name="minutes", operator="<=", value=30),
        NumericFilter(name="servings", operator=">=", value=4)
    ],
    # Tags: Must be BOTH vegetarian AND gluten-free
    dietary_filters=["vegetarian", "gluten_free"],
    # Ingredients: Must have tomato AND basil
    include_ingredients=["tomato", "basil"],
    # Ingredients: Must NOT have nuts or dairy
    exclude_ingredients=["nuts", "dairy"],
    # Ingredients: Must have at least one (cheese OR mozzarella)
    any_ingredients=["cheese", "mozzarella"]
)

results = service.search(
    query="Italian pasta",
    filters=filters,
    limit=10
)
```

### Snowflake: Filter JSON string Format

```sql
-- Snowflake SQL version
-- Example filter in Snowflake
'{
  "numeric_filters": [
    {"name": "minutes", "operator": "<=", "value": 30},
    {"name": "servings", "operator": ">=", "value": 2}
  ],
  "dietary_filters": ["vegetarian", "gluten_free"],
  "include_ingredients": ["tomato"],
  "exclude_ingredients": ["dairy"],
  "any_ingredients": ["basil", "oregano"]
}'
```

### Numeroc Filters
It uses the available numeric columns in the recipes table.

### Numeric Operators

- `">"` = Greater than
- `">="` = Greater than or equal
- `"<"` = Less than
- `"<="` = Less than or equal
- `"="` = Exactly equal


### Available Dietary Tags

The following dietary tags are supported:
vegan, vegetarian, gluten_free, dairy_free, egg_free, nut_free, low_carb, low_fat, low_calorie, no_shell_fish, kosher, halal, non_alcoholic, low_sodium, diabetic, low_cholesterol, low_saturated_fat, low_protein, amish

---

## Index Maintenance

```python
# Python version
# Rebuild index after adding lots of recipes
result = bm25_service.build_index(
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    text_columns=["NAME", "DESCRIPTION", "INGREDIENTS"],
    id_column="ID",
    field_weights={"NAME": 3, "DESCRIPTION": 2, "INGREDIENTS": 1}
)
print(f"Index updated: {result['index_table']}")
```

```sql
-- Snowflake SQL version
-- Rebuild BM25 index
CALL VECTORS.build_bm25_index(
    'ENRICHED.RECIPES_SAMPLE_50K',
    ['NAME', 'DESCRIPTION', 'INGREDIENTS'],
    'ID',
    {'NAME': 3, 'DESCRIPTION': 2, 'INGREDIENTS': 1}
);
```

---

## Updating Embeddings

To update or regenerate the embeddings table after adding new recipes:

```bash
# Run the create_table script to regenerate embeddings
python -m data.embeddings.create_table
```

This script will:
1. Read recipes from your source table (configured in `config.py`)
2. Generate embeddings using the specified model. Note: You need to setup the search service again if the embeddings model changes.
3. Create or update the embeddings table in Snowflake
4. Handle data according to your `DROP_EXISTING_TABLE` setting

**Key Settings for Updates:**
- Set `DROP_EXISTING_TABLE = True` to completely regenerate embeddings
- Set `DROP_EXISTING_TABLE = False` to append new embeddings to existing table
- Adjust `BATCH_SIZE` for better performance with large datasets

For detailed configuration options, see [embeddings README](..\..\..\backend\data\embeddings\README.md).

## Quick Reference

### Vector Search
```python
# Python version
vector_service.search_semantic(
    query="your query",
    top_k=10,
    embeddings_table="VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS",
    filter_conditions=None
)
```

```sql
-- Snowflake SQL version
CALL VECTORS.search_semantic(
    'your query',
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS',
    10,
    NULL
);
```

### BM25 Search
```python
# Python version
bm25_service.search(
    query="your query",
    index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    top_k=10,
    filter_conditions=None
)
```

```sql
-- Snowflake SQL version
CALL VECTORS.search_bm25(
    'your query',
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
    'ENRICHED.RECIPES_SAMPLE_50K',
    10,
    NULL
);
```

### Hybrid Search
```python
# Python version
service.search(
    query="your query",
    filters=None,
    limit=10,
    vector_weight=0.7,
    bm25_weight=0.3,
    index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    embeddings_table="VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS"
)
```

```sql
-- Snowflake SQL version
CALL VECTORS.SEARCH_SIMILAR_RECIPES(
    'your query',
    10,
    NULL,
    0.7,
    0.3,
    'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
    'ENRICHED.RECIPES_SAMPLE_50K',
    'VECTORS.RECIPES_SAMPLE_50K_EMBEDDINGS'
);
```

---
