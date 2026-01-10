# Create Vector Database Service

Generate semantic embeddings for recipe data using GPU-accelerated Snowflake notebooks.

## Table of Contents
1. [Output Database Structure](#output-database-structure)
2. [Quick Start](#quick-start)
3. [What It Does](#what-it-does)
4. [Usage](#usage)
5. [Parameters](#parameters)
6. [Quick Reference](#quick-reference)

---

## Output Database Structure

The vector database service creates a new table with all columns from your source table plus two additional columns:

| Column | Type | Description |
|--------|------|-------------|
| *(source columns)* | *(original types)* | All columns from the source table are preserved |
| `VECTOR` | `VECTOR(FLOAT, <dim>)` | Semantic embedding vector (dimension depends on model) |
| `TEXT_TO_EMBED` | `VARCHAR` | Concatenated text from all embedded columns |

**Example Output Schema:**
```sql
-- For a recipe source table, the output might look like:
ID               NUMBER
NAME             VARCHAR
INGREDIENTS      VARCHAR
STEPS            VARCHAR
DESCRIPTION      VARCHAR
TAGS             VARCHAR
MINUTES          NUMBER
N_STEPS          NUMBER
N_INGREDIENTS    NUMBER
VECTOR           VECTOR(FLOAT, 384)  -- Dimension varies by model
TEXT_TO_EMBED    VARCHAR             -- "Name: ... Ingredients: ... Steps: ..."
```

The `VECTOR` column enables semantic search and similarity matching, while `TEXT_TO_EMBED` shows exactly what text was used to generate each embedding.

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
- Combines specified columns into meaningful text representations
- Generates embeddings using an embedding models
- Stores embeddings alongside original data in a dedicated table
- Preserves all source columns for easy reference and filtering

---

## Usage

### Python: Basic Usage with Defaults
```python
from shared.snowflake.client import SnowflakeClient
from app.services.create_vector_database_service import CreateVectorDatabaseService

# Connect to Snowflake
client = SnowflakeClient()

# Use defaults (first time setup)
service = CreateVectorDatabaseService(
    snowflake_client=client,
    setup=True  # Only needed first time
)

# Create vector database
service.create_vector_database()
```

### Python: Custom Configuration
```python
# Custom configuration for different use cases
service = CreateVectorDatabaseService(
    snowflake_client=client,
    source_table="ENRICHED.MY_RECIPES",
    output_table="VECTORS.MY_EMBEDDINGS",
    id_column="RECIPE_ID",
    columns_to_embed=["TITLE", "INGREDIENTS", "INSTRUCTIONS", "TAGS"],
    embedding_model="BAAI/bge-small-en-v1.5",
    setup=True  # Creates stage and uploads notebook if needed
)

service.create_vector_database()
```

### Snowflake SQL: Manual Execution

If you prefer to execute the notebook directly in Snowflake:

```sql
-- Step 1: Create the notebook (one-time setup)
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

-- Step 3: Execute the notebook with parameters
EXECUTE NOTEBOOK create_vector_db(
    'ENRICHED.RECIPES_SAMPLE_50K',           -- Source table
    'VECTORS.RECIPES_50K_EMBEDDINGS',        -- Output table
    'ID',                                     -- ID column
    'NAME,INGREDIENTS,STEPS,DESCRIPTION',    -- Columns to embed (NO SPACES!)
    'thenlper/gte-small'                     -- Embedding model
);
```

### Using Different Embedding Models
You can use any embedding model available in `sentence-transformers`:

```python
# Small, fast model (384 dimensions)
service = CreateVectorDatabaseService(
    snowflake_client=client,
    embedding_model="thenlper/gte-small"
)

# Medium model (768 dimensions)
service = CreateVectorDatabaseService(
    snowflake_client=client,
    embedding_model="BAAI/bge-small-en-v1.5"
)

# Large model (1024 dimensions)
service = CreateVectorDatabaseService(
    snowflake_client=client,
    embedding_model="BAAI/bge-large-en-v1.5"
)
```

**Important Notes for SQL Execution:**
- Column names in `columns_to_embed` must be comma-separated with **NO SPACES**
- The notebook execution may take several minutes depending on dataset size, embedding model, GPU compute power
- GPU compute pool must be available and properly configured

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
| `embedding_model` | `str` | `"thenlper/gte-small"` | Embedding model from sentence-transformers |

---

## Quick Reference

### Create Vector Database

```python
# Python version
from shared.snowflake.client import SnowflakeClient
from app.services.create_vector_database_service import CreateVectorDatabaseService

client = SnowflakeClient()
service = CreateVectorDatabaseService(snowflake_client=client, setup=True)
service.create_vector_database()
```

```sql
-- Snowflake SQL version
-- One-time setup
CREATE OR REPLACE NOTEBOOK create_vector_db
    FROM @VECTORS.create_vector_db_notebook_stage
    MAIN_FILE = 'create_vector_db.ipynb'
    QUERY_WAREHOUSE = 'NUTRIRAG_PROJECT'
    RUNTIME_NAME = 'SYSTEM$GPU_RUNTIME' 
    COMPUTE_POOL = 'SYSTEM_COMPUTE_POOL_GPU'
    EXTERNAL_ACCESS_INTEGRATIONS = ('training_internet_access');

ALTER NOTEBOOK create_vector_db ADD LIVE VERSION FROM LAST;

-- Execute
EXECUTE NOTEBOOK create_vector_db(
    'ENRICHED.RECIPES_SAMPLE_50K',
    'VECTORS.RECIPES_50K_VECTOR_EMBEDDING',
    'ID',
    'NAME,INGREDIENTS,STEPS,DESCRIPTION',
    'thenlper/gte-small'
);
```
