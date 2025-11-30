# Embedding Models

> Available embedding models for NutriRAG

## Quick Reference

### Local Models (SentenceTransformers)

| Model                                           | Dimension | Notes                     |
| ----------------------------------------------- | --------- | ------------------------- |
| `SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2`        | 384       | Fast, recommended for dev |
| `SENTENCE_TRANSFORMERS_PARAPHRASE_MINILM_L6_V2` | 384       | For paraphrase detection  |

**Requires:** `pip install sentence-transformers`

**Pros:** Works in batch mode, no cloud costs, offline capable

### Snowflake Cortex Models

| Model                      | Dimension | Notes                 |
| -------------------------- | --------- | --------------------- |
| `E5_BASE_V2`               | 768       | Multilingual          |
| `SNOWFLAKE_ARCTIC_EMBED_M` | 768       | Balanced, recommended |
| `SNOWFLAKE_ARCTIC_EMBED_L` | 1024      | Highest quality       |

**Requires:** Snowflake account with Cortex AI enabled

**Pros:** No local compute, optimized for Snowflake

**Cons:** In-memory mode only, cloud costs

## Usage

```python
from shared.models.embedding_models import EmbeddingModel, get_embedding_config

# Get model config
config = get_embedding_config(EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2)
print(config.dimension)  # 384
print(config.is_cortex)  # False
```

## Adding New Models

1. Edit [embedding_models.py](embedding_models.py) - add to `EmbeddingModel` enum
2. Add to `EMBEDDING_CONFIGS` with dimension and `is_cortex` flag
3. Update table above
