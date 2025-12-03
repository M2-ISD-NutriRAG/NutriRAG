"""Internal dataclasses and type definitions for embeddings pipeline."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from shared.snowflake.tables.recipes_sample_table import Table


@dataclass
class TableConfig:
    """Configuration for table creation.

    Attributes:
        source_table: Source table (e.g., RecipesSampleTable).
        target_table: Target table (e.g., RecipesUnifiedEmbeddingsTable).
        columns_to_concat: List of column enums (e.g. RecipesSampleTable) to concatenate for embedding.
        drop_existing: Whether to drop and recreate the target table.
        keep_concatenated_text: Whether to keep the CONCATENATED_TEXT_FOR_RAG column in the final table.
                               Useful for debugging or analysis. Default is False to save storage.
    """

    source_table: type[Table]
    target_table: type[Table]
    columns_to_concat: List[Enum]
    drop_existing: bool = False
    keep_concatenated_text: bool = False


class ProcessingMode(str, Enum):
    """Processing mode for handling datasets.

    Attributes:
        IN_MEMORY: Process all data in memory (suitable for small/medium datasets).
        BATCH: Stream data and process in batches (suitable for large datasets).
    """

    IN_MEMORY = "in_memory"
    BATCH = "batch"


@dataclass
class ProcessingConfig:
    """Configuration for processing mode.

    Attributes:
        mode: Processing mode (in_memory or batch).
        batch_size: Number of rows per batch (only used in batch mode).
    """

    mode: ProcessingMode
    batch_size: Optional[int] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.mode == ProcessingMode.BATCH:
            if (
                self.batch_size is None
                or not isinstance(self.batch_size, int)
                or self.batch_size <= 0
            ):
                raise ValueError(
                    f"batch_size must be a positive integer when mode is BATCH, "
                    f"got: {self.batch_size}"
                )
        elif self.mode == ProcessingMode.IN_MEMORY:
            if self.batch_size is not None:
                raise ValueError(
                    f"batch_size should be None when mode is IN_MEMORY, "
                    f"got: {self.batch_size}"
                )
