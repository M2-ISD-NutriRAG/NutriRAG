# Embeddings Pipeline

> Create Snowflake tables with recipe embeddings for semantic search

## Quick Start

```bash
# Install dependencies (for local models)
pip install sentence-transformers "snowflake-connector-python[pandas]" pyarrow

# Configure
# Edit config.py with your settings

# Run
python -m data.embeddings.create_table
```

## Configuration

Edit [config.py](config.py):

```python
# 1. Choose model (see ../../shared/models/README.md)
EMBEDDING_MODEL = EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2

# 2. Processing mode
PROCESSING_MODE = ProcessingMode.IN_MEMORY  # or ProcessingMode.BATCH
BATCH_SIZE = 1000  # only for batch mode

# 3. Table behavior
DROP_EXISTING_TABLE = True  # True: recreate, False: append
KEEP_CONCATENATED_TEXT = False  # True: keep debug column

# 4. Tables (see ../../shared/snowflake/README.md)
SOURCE_TABLE = RecipesSampleTable
TARGET_TABLE = RecipesUnifiedEmbeddingsTable
```

## Processing Modes

- **`ProcessingMode.IN_MEMORY`** - Fast, works with all models, recommended for < 100k rows
- **`ProcessingMode.BATCH`** - Memory-efficient, local models only, for large datasets

## Common Issues

**"Batch mode only supports local models"** → Use `PROCESSING_MODE = ProcessingMode.IN_MEMORY` or a local model

**"Missing sentence-transformers"** → `pip install sentence-transformers`

**"Dimension mismatch"** → Ensure table EMBEDDING column matches model dimension (e.g. 768 for E5_BASE_V2)

## See Also

- [Embedding Models](../../shared/models/README.md) - Available models
- [Snowflake Tables](../../shared/snowflake/README.md) - Table schemas
