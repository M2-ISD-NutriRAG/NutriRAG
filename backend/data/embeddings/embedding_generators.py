"""Embedding generation strategies (Cortex vs Local)."""

import os
from typing import Any

from snowflake.snowpark import DataFrame, Session
from snowflake.snowpark import functions as F

from shared.utils.console import print_message, MessageType
from shared.models.embedding_models import EmbeddingConfig

from data.embeddings.config import (
    CONCATENATED_TEXT_FOR_RAG,
    EMBEDDING,
    CORTEX_EMBED_FUNCTION_PREFIX,
)
from data.embeddings.text_preparation import _extract_model_name

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class LocalEmbeddingGenerator:
    """Context manager for local embedding generation with proper cleanup.

    Fixes multiprocessing resource tracker warning by properly managing
    SentenceTransformer lifecycle and disabling tokenizers parallelism.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None

    def __enter__(self) -> "LocalEmbeddingGenerator":
        # Disable tokenizers parallelism to avoid fork issues
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.model = SentenceTransformer(self.model_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Explicit cleanup
        if self.model is not None:
            del self.model
        return False

    def encode(self, texts: Any, **kwargs) -> Any:
        """Encode texts using the SentenceTransformer model."""
        return self.model.encode(texts, **kwargs)


def generate_embeddings_cortex(
    dataframe: DataFrame,
    config: EmbeddingConfig,
    text_column: str = CONCATENATED_TEXT_FOR_RAG,
) -> DataFrame:
    """Generates embeddings using Snowflake Cortex.

    Args:
        dataframe: DataFrame containing text to embed.
        config: Embedding configuration.
        text_column: Name of column containing text to embed.

    Returns:
        DataFrame with EMBEDDING column added.
    """
    print_message(
        MessageType.INFO,
        f"🚀 Generating embeddings via Cortex ({config.model.value}, {config.dimension}d)...",
    )

    func_name = f"{CORTEX_EMBED_FUNCTION_PREFIX}{config.dimension}"
    model_name = _extract_model_name(config.model.value)

    return dataframe.with_column(
        EMBEDDING, F.call_builtin(func_name, model_name, F.col(text_column))
    )


def generate_embeddings_local(
    session: Session,
    dataframe: DataFrame,
    config: EmbeddingConfig,
    text_column: str = CONCATENATED_TEXT_FOR_RAG,
) -> DataFrame:
    """Generates embeddings using local SentenceTransformer model with progress bar.

    Args:
        session: Snowflake session.
        dataframe: DataFrame containing text to embed.
        config: Embedding configuration.
        text_column: Name of column containing text to embed.

    Returns:
        DataFrame with EMBEDDING column added.

    Raises:
        RuntimeError: If pandas conversion fails.
        ImportError: If sentence-transformers is not installed.
    """
    print_message(
        MessageType.INFO,
        f"🚀 Generating embeddings locally ({config.model.value}, {config.dimension}d)...",
    )

    try:
        pdf = dataframe.to_pandas()
    except Exception as e:
        raise RuntimeError(
            "Failed to convert Snowpark DataFrame to pandas. This may be due to missing dependencies "
            '(install with: pip install "snowflake-connector-python[pandas]" pyarrow) or data conversion issues.'
        ) from e

    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError(
            "Missing 'sentence-transformers' package. "
            "Install via: pip install sentence-transformers"
        )

    # Use context manager to properly initialize and cleanup the model
    with LocalEmbeddingGenerator(config.model.value) as generator:
        print_message(MessageType.HIGHLIGHT, f"📝 Encoding {len(pdf)} texts...")
        # Use built-in progress bar from SentenceTransformer
        embeddings = generator.encode(
            pdf[text_column].tolist(),
            show_progress_bar=True,  # Show progress during encoding
            batch_size=32,
            normalize_embeddings=False,
        )
        pdf[EMBEDDING] = embeddings.tolist()

    df_with_embeddings = session.create_dataframe(pdf)

    print_message(
        MessageType.HIGHLIGHT, f"🔄 Converting to VECTOR({config.dimension}) format..."
    )
    return df_with_embeddings.with_column(
        EMBEDDING,
        F.sql_expr(f"CAST(EMBEDDING AS VECTOR(FLOAT, {config.dimension}))"),
    )


def generate_embeddings(
    session: Session,
    dataframe: DataFrame,
    config: EmbeddingConfig,
    text_column: str = CONCATENATED_TEXT_FOR_RAG,
) -> DataFrame:
    """Generates embeddings using appropriate method based on model type.

    Args:
        session: Snowflake session.
        dataframe: DataFrame containing text to embed.
        config: Embedding configuration.
        text_column: Name of column containing text to embed.

    Returns:
        DataFrame with EMBEDDING column added.
    """
    if config.is_cortex:
        return generate_embeddings_cortex(dataframe, config, text_column)
    else:
        return generate_embeddings_local(session, dataframe, config, text_column)
