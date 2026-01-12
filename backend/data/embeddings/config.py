"""Embeddings Pipeline Configuration.

Edit the settings below to configure your embedding table creation, then run:
    python -m data.embeddings.create_table

For detailed documentation, see: data/embeddings/README.md

Quick Reference:
- EMBEDDING_MODEL: Choose between Cortex (cloud) or local models
- PROCESSING_MODE: IN_MEMORY (fast) or BATCH (memory-efficient)
- BATCH_SIZE: Number of rows per batch (only for BATCH mode)
- DROP_EXISTING_TABLE: True (recreate) or False (append)
- KEEP_CONCATENATED_TEXT: True (debug) or False (save storage)
"""

from shared.models.embedding_models import EmbeddingModel
from shared.snowflake.tables.recipes_sample_table import (
    RecipesSampleTable,
    RecipesUnifiedEmbeddingsTable,
)

from data.embeddings.types import ProcessingMode

# ============================================================================
# USER CONFIGURATION - Edit these settings
# ============================================================================

# Which embedding model to use
# Options: See shared.models.embedding_models.EmbeddingModel for all available models
EMBEDDING_MODEL = EmbeddingModel.BAAI_BGE_SMALL_EN_V1_5


# Processing mode:
# - ProcessingMode.IN_MEMORY: Process all data at once (recommended for < 100k rows)
# - ProcessingMode.BATCH: Stream and process in chunks (for large datasets, requires local models)
PROCESSING_MODE = ProcessingMode.IN_MEMORY

# Batch size (only used if PROCESSING_MODE = ProcessingMode.BATCH)
BATCH_SIZE = 1000

# Whether to drop and recreate the target table
# - False: Append to existing table (safer default)
# - True: Drop and recreate table (use for full reprocessing)
DROP_EXISTING_TABLE = True

# Whether to keep the concatenated text column in the final table
# - False: Remove to save storage (recommended)
# - True: Keep for debugging/analysis
KEEP_CONCATENATED_TEXT = False

# Source and target tables
SOURCE_TABLE = RecipesSampleTable
TARGET_TABLE = RecipesUnifiedEmbeddingsTable

# ============================================================================
# SYSTEM CONSTANTS - !! Do not edit unless you know what you're doing !!
# ============================================================================

# Column names
CONCATENATED_TEXT_FOR_RAG = (
    RecipesUnifiedEmbeddingsTable.CONCATENATED_TEXT_FOR_RAG.value
)
EMBEDDING = RecipesUnifiedEmbeddingsTable.EMBEDDING.value

# Snowflake constants
CORTEX_EMBED_FUNCTION_PREFIX = "SNOWFLAKE.CORTEX.EMBED_TEXT_"
ARRAY_SEPARATOR = ", "
WRITE_MODE_OVERWRITE = "overwrite"
WRITE_MODE_APPEND = "append"
