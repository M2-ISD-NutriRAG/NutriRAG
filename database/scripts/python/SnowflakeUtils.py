"""
Snowflake database connector module.

Provides the SnowflakeUtils class for managing connections to Snowflake
and executing common database operations.
"""

import logging
import os
import sys
from typing import Dict, List, Optional

import pandas as pd
from snowflake.snowpark import Session

# Add backend to path to import shared modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # NutriRAG root
backend_path = os.path.join(project_root, "backend")
sys.path.insert(0, backend_path)

from shared.snowflake.client import SnowflakeClient


class SnowflakeUtils:
    """Handles Snowflake connection and basic database operations."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Snowflake connector.

        Args:
            config_path: Optional path to JSON config file. Falls back to env vars.
                        Note: Currently unused as SnowflakeClient uses env vars.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = SnowflakeClient(autoconnect=True)
        self.session = self.client.get_snowpark_session()
        self.logger.info("✅ Successfully connected to Snowflake")

    def get_table_columns(self, database: str, schema: str, table: str) -> List[str]:
        """Get list of column names from a Snowflake table."""
        sql = f"""
        SELECT COLUMN_NAME 
        FROM {database}.INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{schema}' 
        AND TABLE_NAME = '{table.upper()}'
        ORDER BY ORDINAL_POSITION
        """
        try:
            rows = self.session.sql(sql).collect()
            return [r['COLUMN_NAME'] for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting table columns: {e}")
            return []

    def ensure_table(
        self,
        database: str,
        schema: str,
        table: str,
        columns_sql: Dict[str, str]
    ) -> None:
        """Create a table if it doesn't exist, or add missing columns."""
        cols = ",\n    ".join([f"{c} {t}" for c, t in columns_sql.items()])
        sql = f"CREATE TABLE IF NOT EXISTS {database}.{schema}.{table} (\n    {cols}\n);"
        self.logger.info(f"Creating table {database}.{schema}.{table} (if not exists)...")
        self.safe_execute(sql)
        
        # Add any missing columns
        existing = [c.upper() for c in self.get_table_columns(database, schema, table)]
        for col, col_type in columns_sql.items():
            if col.upper() not in existing:
                alter_sql = f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {col} {col_type}"
                self.logger.info(f"Adding missing column: {col} {col_type}")
                self.safe_execute(alter_sql)

    def safe_execute(self, sql: str):
        """Execute SQL statement safely with error handling."""
        try:
            return self.session.sql(sql).collect()
        except Exception as e:
            self.logger.error(f"SQL execution error:\n{sql}\n-> {e}")
            raise

    def write_pandas(
        self,
        df: pd.DataFrame,
        database: str,
        schema: str,
        table: str,
        overwrite: bool = True,
        auto_create_table=False
    ):
        """Write a Pandas DataFrame to Snowflake."""
        minimal_schema = {col.upper(): "VARCHAR" for col in df.columns}
        self.ensure_table(database, schema, table, minimal_schema)
        self.logger.info(f"Writing {len(df)} rows to {database}.{schema}.{table}")
        result = self.session.write_pandas(
            df,
            table_name=table,
            schema=schema,
            database=database,
            overwrite=overwrite
        )
        self.logger.info("✅ DataFrame write completed")
        return result

    def close(self) -> None:
        """Close the Snowflake session."""
        if self.client:
            self.client.close()
            self.logger.info("Session closed")
