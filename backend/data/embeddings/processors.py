"""Processing strategies for embedding generation (in-memory vs batch)."""

from typing import Any, Iterator, List, Literal

import pandas as pd
from snowflake.snowpark import DataFrame, Session
from snowflake.snowpark import functions as F

from shared.utils.console import print_message, MessageType
from shared.models.embedding_models import EmbeddingConfig

from data.embeddings.config import (
    CONCATENATED_TEXT_FOR_RAG,
    EMBEDDING,
    WRITE_MODE_OVERWRITE,
    WRITE_MODE_APPEND,
)
from data.embeddings.embedding_generators import generate_embeddings
from data.embeddings.text_preparation import prepare_text_column
from data.embeddings.types import TableConfig, ProcessingConfig

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class EmbeddingPipeline:
    """Pipeline for orchestrating the embedding generation workflow.

    Encapsulates common logic between in-memory and batch processing modes.
    """

    def __init__(
        self,
        session: Session,
        table_config: TableConfig,
        embedding_config: EmbeddingConfig,
    ):
        """Initialize the pipeline.

        Args:
            session: Snowflake session.
            table_config: Table configuration.
            embedding_config: Embedding configuration.
        """
        self.session = session
        self.table_config = table_config
        self.embedding_config = embedding_config

    def _prepare_dataframe(self, source_df: DataFrame) -> DataFrame:
        """Prepare DataFrame by adding concatenated text column.

        Args:
            source_df: Source DataFrame.

        Returns:
            DataFrame with CONCATENATED_TEXT_FOR_RAG column added.
        """
        return prepare_text_column(source_df, self.table_config.columns_to_concat)

    def _finalize_dataframe(self, df_with_embeddings: DataFrame) -> DataFrame:
        """Finalize DataFrame by optionally removing concatenated text column.

        Args:
            df_with_embeddings: DataFrame with embeddings.

        Returns:
            Final DataFrame ready to be written.
        """
        if self.table_config.keep_concatenated_text:
            print_message(
                MessageType.INFO,
                f"📝 Keeping {CONCATENATED_TEXT_FOR_RAG} column for debugging/analysis",
            )
            return df_with_embeddings
        else:
            return df_with_embeddings.drop(CONCATENATED_TEXT_FOR_RAG)

    def _save_to_table(
        self, df_final: DataFrame, mode: Literal["overwrite", "append"]
    ) -> None:
        """Save DataFrame to target table.

        Args:
            df_final: Final DataFrame to save.
            mode: Write mode ('overwrite' or 'append').
        """
        print_message(
            MessageType.SUCCESS,
            f"💾 Saving to '{self.table_config.target_table.NAME}' (mode: {mode})...",
        )
        df_final.write.mode(mode).save_as_table(self.table_config.target_table.NAME)
        print_message(MessageType.SUCCESS, "✓ Complete.")

    def process_in_memory(self, source_df: DataFrame) -> None:
        """Process entire dataset in memory.

        Args:
            source_df: Source DataFrame.
        """
        print_message(MessageType.STAGE, "In-Memory Processing", width=40)

        # Prepare text column
        df_with_text = self._prepare_dataframe(source_df)

        # Generate embeddings
        df_with_embeddings = generate_embeddings(
            self.session, df_with_text, self.embedding_config
        )

        # Finalize and save
        df_final = self._finalize_dataframe(df_with_embeddings)
        mode = (
            WRITE_MODE_OVERWRITE
            if self.table_config.drop_existing
            else WRITE_MODE_APPEND
        )
        self._save_to_table(df_final, mode)


class BatchProcessor:
    """Manages batch processing state and operations."""

    def __init__(
        self,
        session: Session,
        table_config: TableConfig,
        embedding_config: EmbeddingConfig,
        batch_size: int,
    ):
        """Initialize batch processor.

        Args:
            session: Snowflake session.
            table_config: Table configuration.
            embedding_config: Embedding configuration.
            batch_size: Number of rows per batch.
        """
        self.session = session
        self.table_config = table_config
        self.embedding_config = embedding_config
        self.batch_size = batch_size
        self.total_processed = 0
        self.is_first_batch = True

    def _stream_batches(self, iterator: Iterator) -> Iterator[List[dict]]:
        """Yield batches of rows from iterator.

        Args:
            iterator: Snowpark DataFrame iterator.

        Yields:
            Lists of row dictionaries.
        """
        batch = []
        for row in iterator:
            batch.append(row.as_dict())
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
        if batch:  # Yield remaining rows
            yield batch

    def _determine_write_mode(self) -> Literal["overwrite", "append"]:
        """Determine write mode based on batch position and drop flag.

        Returns:
            Write mode ('overwrite' or 'append').

        Note:
            When drop_existing=False and the table doesn't exist, the first batch
            will use 'append' mode. Snowpark's .write.mode("append") automatically
            creates the table if it doesn't exist.
        """
        return (
            WRITE_MODE_OVERWRITE
            if (self.is_first_batch and self.table_config.drop_existing)
            else WRITE_MODE_APPEND
        )

    def _process_batch_chunk(
        self,
        batch_data: List[dict[str, Any]],
        model: 'SentenceTransformer',
    ) -> None:
        """Process a single batch of data and save to Snowflake.

        Args:
            batch_data: List of row dictionaries.
            model: SentenceTransformer model instance.
        """
        if not batch_data:
            return

        # Convert to pandas DataFrame
        pdf = pd.DataFrame(batch_data)

        # Generate embeddings
        embeddings = model.encode(
            pdf[CONCATENATED_TEXT_FOR_RAG].tolist(),
            show_progress_bar=False,
            batch_size=32,
            normalize_embeddings=False,
        )
        pdf[EMBEDDING] = embeddings.tolist()

        # Conditionally drop the concatenated text column
        if not self.table_config.keep_concatenated_text:
            pdf = pdf.drop(columns=[CONCATENATED_TEXT_FOR_RAG])

        # Convert to Snowpark DataFrame and cast to VECTOR type
        df_snow = self.session.create_dataframe(pdf)
        df_final = df_snow.with_column(
            EMBEDDING,
            F.sql_expr(
                f"CAST(EMBEDDING AS VECTOR(FLOAT, {self.embedding_config.dimension}))"
            ),
        )

        # Save to table
        write_mode = self._determine_write_mode()
        df_final.write.mode(write_mode).save_as_table(
            self.table_config.target_table.NAME
        )
        print_message(MessageType.SUCCESS, f"   ✓ Saved batch ({len(batch_data)} rows)")

    def _drop_existing_table_if_needed(self) -> None:
        """Drop existing table if drop_existing flag is set."""
        if self.table_config.drop_existing:
            print_message(
                MessageType.WARNING,
                f"🗑️  Dropping table '{self.table_config.target_table.NAME}' if exists...",
            )
            try:
                self.session.table(self.table_config.target_table.NAME).drop_table()
            except Exception as e:
                # Table likely doesn't exist, which is fine
                print_message(
                    MessageType.INFO,
                    f"   Table doesn't exist or couldn't be dropped: {type(e).__name__}",
                )

    def process_batch_mode(
        self, source_df: DataFrame, model: 'SentenceTransformer'
    ) -> None:
        """Process dataset in batches using streaming.

        Args:
            source_df: Source DataFrame.
            model: SentenceTransformer model instance.
        """
        print_message(
            MessageType.STAGE,
            f"Batch Processing (batch_size={self.batch_size})",
            width=40,
        )

        if self.table_config.keep_concatenated_text:
            print_message(
                MessageType.INFO,
                f"📝 Keeping {CONCATENATED_TEXT_FOR_RAG} column for debugging/analysis",
            )

        # Drop table if needed
        self._drop_existing_table_if_needed()

        # Prepare text column
        df_with_text = prepare_text_column(
            source_df, self.table_config.columns_to_concat
        )

        # Stream and process batches
        print_message(MessageType.HIGHLIGHT, "📡 Streaming data from Snowflake...")
        iterator = df_with_text.to_local_iterator()

        for batch_data in self._stream_batches(iterator):
            print_message(
                MessageType.INFO,
                f"Processing batch {self.total_processed} to {self.total_processed + len(batch_data)}...",
            )
            self._process_batch_chunk(batch_data, model)

            self.total_processed += len(batch_data)
            self.is_first_batch = False

        print_message(MessageType.SUCCESS, "\n✓ Batch Processing Complete")


def process_in_memory(
    session: Session,
    source_df: DataFrame,
    table_config: TableConfig,
    embedding_config: EmbeddingConfig,
) -> None:
    """Process entire dataset in memory and write to target table.

    Args:
        session: Snowflake session.
        source_df: Source DataFrame.
        table_config: Table configuration.
        embedding_config: Embedding configuration.
    """
    pipeline = EmbeddingPipeline(session, table_config, embedding_config)
    pipeline.process_in_memory(source_df)


def process_batch_mode(
    session: Session,
    source_df: DataFrame,
    table_config: TableConfig,
    embedding_config: EmbeddingConfig,
    processing_config: ProcessingConfig,
) -> None:
    """Process dataset in batches using streaming to minimize memory usage.

    Args:
        session: Snowflake session.
        source_df: Source DataFrame.
        table_config: Table configuration.
        embedding_config: Embedding configuration.
        processing_config: Processing configuration.

    Raises:
        ValueError: If Cortex models are used (batch mode requires local models).
        ImportError: If sentence-transformers is not installed.
    """
    # Validate requirements
    if embedding_config.is_cortex:
        raise ValueError(
            "Batch mode currently only supports local models because it requires "
            "streaming data processing. Use in-memory mode for Cortex models."
        )

    if not HAS_SENTENCE_TRANSFORMERS:
        raise ImportError(
            "Missing 'sentence-transformers' package required for batch mode. "
            "Install via: pip install sentence-transformers"
        )

    # Load model
    print_message(
        MessageType.HIGHLIGHT, f"📦 Loading model '{embedding_config.model.value}'..."
    )
    model = SentenceTransformer(embedding_config.model.value)

    # Process batches
    processor = BatchProcessor(
        session, table_config, embedding_config, processing_config.batch_size
    )
    processor.process_batch_mode(source_df, model)
