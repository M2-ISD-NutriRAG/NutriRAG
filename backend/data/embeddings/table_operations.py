"""Snowflake table interactions and validation."""

from typing import Optional

from snowflake.snowpark import DataFrame, Session

from shared.utils.console import print_message, MessageType
from shared.snowflake.tables import Table

from data.embeddings.config import EMBEDDING
from data.embeddings.types import TableConfig


def _table_exists(session: Session, table: type[Table]) -> bool:
    """Check if a table exists in Snowflake.

    Args:
        session: Snowflake session.
        table: Table class to check.

    Returns:
        True if table exists, False otherwise.
    """
    try:
        df = session.table(table.NAME)
        _ = df.schema  # Verify table exists
        return True
    except Exception:
        return False


def get_source_dataframe(
    session: Session, table_config: TableConfig
) -> Optional[DataFrame]:
    """Retrieves source DataFrame based on configuration.

    Args:
        session: Snowflake session.
        table_config: Table configuration.

    Returns:
        Source DataFrame or None if target doesn't exist and no source specified.
    """
    target_exists = _table_exists(session, table_config.target_table)

    if not target_exists:
        # Target doesn't exist - must create from source
        print_message(
            MessageType.INFO,
            f"ℹ️  Target table '{table_config.target_table.NAME}' does not exist.",
        )
        if not table_config.source_table:
            print_message(MessageType.ERROR, "❌ Error: No source table specified.")
            return None
        print_message(
            MessageType.INFO, f"   → Creating from '{table_config.source_table.NAME}'"
        )
        return session.table(table_config.source_table.NAME)

    # Target exists
    print_message(
        MessageType.INFO, f"ℹ️  Target table '{table_config.target_table.NAME}' exists."
    )

    if table_config.drop_existing:
        if table_config.source_table:
            print_message(
                MessageType.INFO,
                f"   → Drop mode: Reloading from '{table_config.source_table.NAME}'",
            )
            return session.table(table_config.source_table.NAME)
        else:
            print_message(MessageType.INFO, "   → Drop mode: Reusing existing data")
            return session.table(table_config.target_table.NAME)
    else:
        print_message(MessageType.INFO, "   → Append mode")
        return session.table(table_config.target_table.NAME)


def _verify_embedding_column(
    schema_fields, table_name: str, expected_dimension: Optional[int] = None
):
    """Verify that EMBEDDING column exists and has correct dimension.

    Args:
        schema_fields: List of schema fields.
        table_name: Name of the table being verified.
        expected_dimension: Expected vector dimension.

    Raises:
        ValueError: If EMBEDDING column is missing or has incorrect dimension.
    """
    embedding_field = None
    for field in schema_fields:
        if field.name == EMBEDDING:
            embedding_field = field
            break

    if embedding_field is None:
        raise ValueError(f"EMBEDDING column not found in table {table_name}")

    print_message(
        MessageType.SUCCESS, f"✓ EMBEDDING column type: {embedding_field.datatype}"
    )

    # Validate dimension if specified
    if expected_dimension:
        datatype_str = str(embedding_field.datatype)
        # Check for both formats: "VECTOR(FLOAT, 768)" and "VectorType(float,768)"
        if not (
            f"VECTOR(FLOAT, {expected_dimension})" in datatype_str
            or f"VectorType(float,{expected_dimension})" in datatype_str
        ):
            raise ValueError(
                f"EMBEDDING dimension mismatch. Expected {expected_dimension}, "
                f"but got: {embedding_field.datatype}"
            )
        print_message(
            MessageType.SUCCESS, f"✓ Vector dimension matches expected: {expected_dimension}"
        )


def _check_row_count(dataframe: DataFrame) -> int:
    """Check and display row count.

    Args:
        dataframe: DataFrame to count rows from.

    Returns:
        Number of rows in the dataframe.
    """
    row_count = dataframe.count()
    print_message(MessageType.SUCCESS, f"✓ Total rows: {row_count}")

    if row_count == 0:
        print_message(MessageType.WARNING, "⚠ Warning: Table is empty")

    return row_count


def _display_sample_data(dataframe: DataFrame):
    """Display sample data from the table.

    Args:
        dataframe: DataFrame to display samples from.
    """
    print_message(MessageType.INFO, "\n--- Sample Data ---")

    # Check if "NAME" column exists in the table schema
    available_columns = [field.name for field in dataframe.schema.fields]
    columns_to_show = []

    if "NAME" in available_columns:
        columns_to_show.append("NAME")
    elif available_columns:
        # Select the first column as a fallback (could be ID, etc.)
        columns_to_show.append(available_columns[0])
    else:
        print_message(MessageType.WARNING, "No columns available to display sample data.")
        return

    columns_to_show.append(EMBEDDING)

    try:
        dataframe.select(*columns_to_show).show(2)
    except Exception as e:
        print_message(MessageType.ERROR, f"⚠ Error displaying sample data: {e}")


def verify_table_schema(
    session: Session, table: type[Table], expected_dimension: Optional[int] = None
) -> None:
    """Verifies and displays the schema of the created table.

    Args:
        session: Snowflake session.
        table: Table class to verify.
        expected_dimension: Expected vector dimension to validate against (optional).

    Raises:
        ValueError: If EMBEDDING column is missing or has incorrect dimension.
    """
    print_message(MessageType.HEADER, f"Schema Verification: {table.NAME}", width=40)

    df = session.table(table.NAME)

    # Verify EMBEDDING column exists and has correct dimension
    _verify_embedding_column(df.schema.fields, table.NAME, expected_dimension)

    # Check row count
    row_count = _check_row_count(df)

    # Display sample data if table is not empty
    if row_count > 0:
        _display_sample_data(df)
