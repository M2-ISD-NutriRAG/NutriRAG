"""Embedding model definitions and configurations."""

from dataclasses import dataclass
from enum import Enum


class EmbeddingModel(str, Enum):
    # Local models
    SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2 = "sentence-transformers/all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_PARAPHRASE_MINILM_L6_V2 = (
        "sentence-transformers/paraphrase-MiniLM-L6-v2"
    )
    BAAI_BGE_SMALL_EN_V1_5 = "BAAI/bge-small-en-v1.5"

    # Snowflake models
    E5_BASE_V2 = "e5-base-v2"
    SNOWFLAKE_ARCTIC_EMBED_M = "snowflake-arctic-embed-m"
    SNOWFLAKE_ARCTIC_EMBED_L = "snowflake-arctic-embed-l"

    @classmethod
    def default(cls):
        # Return the default embedding model
        # TODO: Choose appropriate default
        return cls.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation.

    Attributes:
        model: The embedding model to use.
        dimension: Vector dimension for the model.
        is_cortex: Whether the model uses Snowflake Cortex.
    """

    model: EmbeddingModel
    dimension: int
    is_cortex: bool


# Mapping of embedding models to their configurations
EMBEDDING_CONFIGS: dict[EmbeddingModel, EmbeddingConfig] = {
    EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2: EmbeddingConfig(
        model=EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2,
        dimension=384,
        is_cortex=False,
    ),
    EmbeddingModel.SENTENCE_TRANSFORMERS_PARAPHRASE_MINILM_L6_V2: EmbeddingConfig(
        model=EmbeddingModel.SENTENCE_TRANSFORMERS_PARAPHRASE_MINILM_L6_V2,
        dimension=384,
        is_cortex=False,
    ),
    EmbeddingModel.BAAI_BGE_SMALL_EN_V1_5: EmbeddingConfig(
        model=EmbeddingModel.BAAI_BGE_SMALL_EN_V1_5,
        dimension=384,
        is_cortex=False,
    ),
    EmbeddingModel.E5_BASE_V2: EmbeddingConfig(
        model=EmbeddingModel.E5_BASE_V2,
        dimension=768,
        is_cortex=True,
    ),
    EmbeddingModel.SNOWFLAKE_ARCTIC_EMBED_M: EmbeddingConfig(
        model=EmbeddingModel.SNOWFLAKE_ARCTIC_EMBED_M,
        dimension=768,
        is_cortex=True,
    ),
    EmbeddingModel.SNOWFLAKE_ARCTIC_EMBED_L: EmbeddingConfig(
        model=EmbeddingModel.SNOWFLAKE_ARCTIC_EMBED_L,
        dimension=1024,
        is_cortex=True,
    ),
}


def get_embedding_config(model: EmbeddingModel) -> EmbeddingConfig:
    """Get the configuration for a specific embedding model.

    Args:
        model: The embedding model to get configuration for.

    Returns:
        The configuration for the specified model.

    Raises:
        KeyError: If the model is not found in the configurations.
    """
    return EMBEDDING_CONFIGS[model]
