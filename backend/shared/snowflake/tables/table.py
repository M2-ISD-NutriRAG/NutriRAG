from abc import abstractmethod

from enum import Enum
from typing import List


def define_snowflake_table(
    SNOWFLAKE_DATABASE: str, SCHEMA_NAME: str, TABLE_NAME: str
):
    """Decorator for Snowflake table classes.

    Args:
        SNOWFLAKE_DATABASE: Name of the Snowflake database.
        SCHEMA_NAME: Name of the Snowflake schema.
        TABLE_NAME: Name of the Snowflake table.
    """

    def decorator(cls):
        cls._snowflake_database = SNOWFLAKE_DATABASE
        cls._schema_name = SCHEMA_NAME
        cls._table_name = TABLE_NAME
        return cls

    return decorator


class Table(str, Enum):
    """Base class for table enums with common functionality."""

    _snowflake_database: str
    _schema_name: str
    _table_name: str

    @classmethod
    def get_table_name(cls) -> str:
        return cls._table_name

    @classmethod
    def get_full_table_name(cls) -> str:
        return f"{cls._snowflake_database}.{cls._schema_name}.{cls._table_name}"

    @abstractmethod
    def get_columns_to_concat_for_embedding(cls) -> List[str]:
        """Returns a list of columns to concatenate for embedding.

        Raises:
            NotImplementedError: If the subclass doesn't implement this method.
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement get_columns_to_concat_for_embedding() method."
        )

    @staticmethod
    def get_column_names() -> List[str]:
        """Returns a list of all column names defined in the table enum."""
        return [column.value for column in Table]
