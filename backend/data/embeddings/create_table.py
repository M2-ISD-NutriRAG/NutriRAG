"""Main orchestration and CLI entry point for embeddings table creation."""

from snowflake.snowpark import Session

from shared.utils.console import print_message, MessageType
from shared.models.embedding_models import get_embedding_config
from shared.snowflake.client import SnowflakeClient

from data.embeddings.config import (
    EMBEDDING_MODEL,
    PROCESSING_MODE,
    BATCH_SIZE,
    DROP_EXISTING_TABLE,
    KEEP_CONCATENATED_TEXT,
    SOURCE_TABLE,
    TARGET_TABLE,
)
from data.embeddings.processors import process_in_memory, process_batch_mode
from data.embeddings.table_operations import (
    get_source_dataframe,
    verify_table_schema,
)
from data.embeddings.types import TableConfig, ProcessingConfig, ProcessingMode


def create_embeddings_table(
    session: Session,
    table_config: TableConfig,
    embedding_config,
    processing_config: ProcessingConfig,
) -> None:
    """Main function to create embeddings table.

    Orchestrates the entire pipeline:
    1. Validates configuration
    2. Retrieves source DataFrame
    3. Processes data (in-memory or batch)
    4. Saves to target table

    Args:
        session: Snowflake session.
        table_config: Table configuration.
        embedding_config: Embedding configuration.
        processing_config: Processing configuration.
    """
    print_message(
        MessageType.HEADER,
        f"Creating Embeddings Table: {table_config.target_table.get_full_table_name()}",
        width=60,
    )

    # Retrieve source DataFrame
    source_df = get_source_dataframe(session, table_config)
    if source_df is None:
        return

    # Display configuration
    print_message(
        MessageType.INFO,
        f"\n📋 Columns to concatenate: {table_config.columns_to_concat}",
    )

    # Process based on mode
    if processing_config.mode == ProcessingMode.IN_MEMORY:
        process_in_memory(session, source_df, table_config, embedding_config)
    else:
        process_batch_mode(
            session,
            source_df,
            table_config,
            embedding_config,
            processing_config,
        )


def main() -> None:
    """Main execution function.

    Loads configuration from config.py and runs the embedding table creation pipeline.
    """
    # Create Snowflake client using context manager
    with SnowflakeClient() as client:
        session = client.get_snowpark_session()

        # Build configurations from config.py
        table_config = TableConfig(
            source_table=SOURCE_TABLE,
            target_table=TARGET_TABLE,
            columns_to_concat=SOURCE_TABLE.get_columns_to_concat_for_embedding(),
            drop_existing=DROP_EXISTING_TABLE,
            keep_concatenated_text=KEEP_CONCATENATED_TEXT,
        )

        embedding_config = get_embedding_config(EMBEDDING_MODEL)

        # Build processing config
        processing_config = ProcessingConfig(
            mode=PROCESSING_MODE,
            batch_size=BATCH_SIZE
            if PROCESSING_MODE == ProcessingMode.BATCH
            else None,
        )

        # Create table
        create_embeddings_table(
            session, table_config, embedding_config, processing_config
        )

        # Verify results
        verify_table_schema(
            session, table_config.target_table, embedding_config.dimension
        )


if __name__ == "__main__":
    main()
