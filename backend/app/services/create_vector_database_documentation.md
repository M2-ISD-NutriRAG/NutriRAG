# Create Vector Database Service

Generate semantic embeddings for recipe data using GPU-accelerated Snowflake notebooks.

## Table of Contents
1. [Quick Start](#quick-start)
2. [What It Does](#what-it-does)
3. [Python Usage](#python-usage)
4. [Direct Snowflake SQL](#direct-snowflake-sql)
5. [Parameters](#parameters)
6. [Embedding Models](#embedding-models)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Quick Reference](#quick-reference)

---

## Quick Start

### First Time Setup
```python
from shared.snowflake.client import SnowflakeClient
from app.services.create_vector_database_service import CreateVectorDatabaseService

# Connect to Snowflake
client = SnowflakeClient()

# Initialize with setup=True to create stage and upload notebook
service = CreateVectorDatabaseService(
    snowflake_client=client,
    setup=True  # Creates stage and uploads notebook
)

# Create the vector database
service.create_vector_database()

print("Vector embeddings created successfully!")
```

---

## What It Does

The Create Vector Database Service generates semantic embeddings for your recipe data, enabling powerful vector search capabilities. It:

- Reads recipes from your Snowflake table
- Generates embeddings using embeddings models
- Stores embeddings in a dedicated table

---

## Python Usage

### Custom Configuration
```python
service = CreateVectorDatabaseService(
    snowflake_client=client,
    source_table="ENRICHED.MY_RECIPES",
    output_table="VECTORS.MY_EMBEDDINGS",
    id_column="RECIPE_ID",
    columns_to_embed=["TITLE", "INGREDIENTS", "INSTRUCTIONS", "TAGS"],
    embedding_model="BAAI/bge-small-en-v1.5",
    setup=True
)

service.create_vector_database()
```

### Using Different Embedding Models

you can use any emebdding models that exist in snetence-transformer

---

## Direct Snowflake SQL

### Manual Execution 

If you prefer to execute the notebook directly in Snowflake:
```sql
-- Step 1: Create the notebook
CREATE OR REPLACE NOTEBOOK create_vector_db
    FROM @VECTORS.create_vector_db_notebook_stage
    MAIN_FILE = 'create_vector_db.ipynb'
    QUERY_WAREHOUSE = 'NUTRIRAG_PROJECT'
    RUNTIME_NAME = 'SYSTEM$GPU_RUNTIME' 
    COMPUTE_POOL = 'SYSTEM_COMPUTE_POOL_GPU'
    EXTERNAL_ACCESS_INTEGRATIONS = ('training_internet_access');

-- Step 2: Activate the notebook
ALTER NOTEBOOK create_vector_db 
    ADD LIVE VERSION FROM LAST;

-- Step 3: Execute the notebook
EXECUTE NOTEBOOK create_vector_db(
    'ENRICHED.RECIPES_SAMPLE_50K',           -- Source table
    'VECTORS.RECIPES_50K_EMBEDDINGS',        -- Output table
    'ID',                                     -- ID column
    'NAME,INGREDIENTS,STEPS,DESCRIPTION',    -- Columns to embed (NO SPACES!)
    'thenlper/gte-small'                     -- Embedding model
);
```

---

## Parameters

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `snowflake_client` | `SnowflakeClient` | `None` | Snowflake client instance (creates new if None) |
| `stage_name` | `str` | `"VECTORS.create_vector_db_notebook_stage"` | Stage for storing the notebook |
| `notebook_name` | `str` | `"create_vector_db"` | Name of the notebook |
| `setup` | `bool` | `False` | Whether to create stage and upload notebook |
| `source_table` | `str` | `"ENRICHED.RECIPES_SAMPLE_50K"` | Table containing recipes to embed |
| `output_table` | `str` | `"VECTORS.RECIPES_50K_VECTOR_EMBEDDING"` | Where to store embeddings |
| `id_column` | `str` | `"ID"` | Unique identifier column |
| `columns_to_embed` | `List[str]` | `["NAME", "INGREDIENTS", "STEPS", "DESCRIPTION"]` | Columns to combine for embeddings |
| `embedding_model` | `str` | `"thenlper/gte-small"` | Embedding model to use |


## Quick Reference

### Default Configuration
```python
CreateVectorDatabaseService(
    stage_name="VECTORS.create_vector_db_notebook_stage",
    notebook_name="create_vector_db",
    source_table="ENRICHED.RECIPES_SAMPLE_50K",
    output_table="VECTORS.RECIPES_50K_VECTOR_EMBEDDING",
    id_column="ID",
    columns_to_embed=["NAME", "INGREDIENTS", "STEPS", "DESCRIPTION"],
    embedding_model="thenlper/gte-small"
)
```

