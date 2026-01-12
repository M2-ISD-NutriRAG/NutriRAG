"""Text cleaning and preparation utilities for embedding generation."""

from enum import Enum
from typing import Any, List

from snowflake.snowpark import DataFrame
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import ArrayType

from shared.utils.console import print_message, MessageType

from data.embeddings.config import ARRAY_SEPARATOR, CONCATENATED_TEXT_FOR_RAG


def _extract_model_name(model_value: str) -> str:
    """Extract model name from full path (e.g., 'org/model' -> 'model').

    Args:
        model_value: Full model identifier (may include organization prefix).

    Returns:
        Extracted model name without path prefix.
    """
    return model_value.split("/")[-1] if "/" in model_value else model_value


def clean_column_expression(column_name: str, data_type: Any) -> Any:
    """Creates a cleaned column expression for text concatenation.

    Args:
        column_name: Name of the column to clean.
        data_type: Snowpark data type of the column.

    Returns:
        Snowpark column expression with cleaning transformations applied.
    """
    col_expr = F.col(column_name)

    if isinstance(data_type, ArrayType):
        col_expr = F.array_to_string(col_expr, F.lit(ARRAY_SEPARATOR))
    else:
        col_expr = F.to_varchar(col_expr)

    return F.coalesce(F.trim(F.lower(col_expr)), F.lit(""))


def prepare_text_column(dataframe: DataFrame, columns: List[Enum]) -> DataFrame:
    """Prepares a concatenated text column from specified columns.

    Args:
        dataframe: Source Snowpark DataFrame.
        columns: List of columns (Enums) to concatenate.

    Returns:
        DataFrame with added CONCATENATED_TEXT_FOR_RAG column.

    Raises:
        ValueError: If no valid columns found.
    """
    schema_dict = {
        field.name: field.datatype for field in dataframe.schema.fields
    }
    cleaned_expressions = []

    for column in columns:
        column_name = column.value
        if column_name not in schema_dict:
            print_message(
                MessageType.WARNING,
                f"⚠ Column '{column_name}' not found. Skipping.",
            )
            continue

        cleaned_expr = clean_column_expression(
            column_name, schema_dict[column_name]
        )
        cleaned_expressions.append(cleaned_expr)

    if not cleaned_expressions:
        raise ValueError(f"No valid columns found from: {columns}")

    concatenated_text = F.concat_ws(F.lit(" "), *cleaned_expressions)
    return dataframe.with_column(CONCATENATED_TEXT_FOR_RAG, concatenated_text)
