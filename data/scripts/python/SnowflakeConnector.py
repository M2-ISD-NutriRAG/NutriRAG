"""
Snowflake database connector module.

Provides the SnowflakeConnector class for managing connections to Snowflake
and executing common database operations.
"""

import json
import logging
import os
from typing import Dict, List, Optional
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

import pandas as pd
from snowflake.snowpark import Session

from dotenv import load_dotenv

load_dotenv()

class SnowflakeConnector:
    """Handles Snowflake connection and basic database operations."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Snowflake connector.

        Args:
            config_path: Optional path to JSON config file. Falls back to env vars.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = self._create_session(config_path)

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load Snowflake configuration from JSON or environment variables."""
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)

        # Fallback to environment variables
        env = os.environ
        cfg = {}
        if env.get("SNOWFLAKE_ACCOUNT","OEWWHQK-TG55216"):
            cfg.update({
                "account": env.get("SNOWFLAKE_ACCOUNT"),
                "user": env.get("SNOWFLAKE_USER"),
                "role": env.get("SNOWFLAKE_ROLE"),
            })
            
            # Privilege key-based authentication over password
            private_key_path = env.get("SNOWFLAKE_PRIVATE_KEY_PATH","/Users/cameliamazouz/Documents/M2/projetML/NutriRAG/backend/.ssh/rsa_key.p8")
            
            if private_key_path and os.path.exists(private_key_path):
                # Load private key for key-pair authentication
                self.logger.info("Using private key authentication")
                with open(private_key_path, "rb") as key_file:
                    private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,
                        backend=default_backend()
                    )
                
                # Get private key bytes
                pkb = private_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                cfg["private_key"] = pkb
            elif env.get("SNOWFLAKE_PASSWORD"):
                # Fallback to password authentication
                self.logger.info("Using password authentication")
                cfg["password"] = env.get("SNOWFLAKE_PASSWORD")
            else:
                raise ValueError(
                    "Authentication credentials not found. Set either:\n"
                    "  - SNOWFLAKE_PRIVATE_KEY_PATH (recommended)\n"
                    "  - SNOWFLAKE_PASSWORD (fallback)"
                )
            
            # Warehouse, database and schema are optional but can be set via env
            if env.get("SNOWFLAKE_WAREHOUSE"):
                cfg["warehouse"] = env.get("SNOWFLAKE_WAREHOUSE")
            if env.get("SNOWFLAKE_DATABASE"):
                cfg["database"] = env.get("SNOWFLAKE_DATABASE")
            if env.get("SNOWFLAKE_SCHEMA"):
                cfg["schema"] = env.get("SNOWFLAKE_SCHEMA")

        return cfg

    def _create_session(self, config_path: Optional[str]) -> Session:
        """Create and return a Snowflake session."""
        cfg = self._load_config(config_path)
        if not cfg or not cfg.get("account"):
            raise ValueError(
                "Snowflake config not found. Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, "
                "SNOWFLAKE_ROLE, and authentication credentials (private key or password)."
            )

        self.logger.info(f"Connecting to Snowflake account: {cfg['account']}")
        auth_method = "private key" if "private_key" in cfg else "password"
        self.logger.info(f"Authentication method: {auth_method}")
        
        builder = Session.builder.configs(cfg)
        session = builder.create()
        self.logger.info("✅ Successfully connected to Snowflake")
        return session

    def table_exists(self, database: str, schema: str, table: str) -> bool:
        """Check if a table exists in Snowflake."""
        sql = f"SHOW TABLES IN {database}.{schema} LIKE '{table}'"
        try:
            res = self.session.sql(sql).collect()
            return len(res) > 0
        except Exception as e:
            self.logger.error(f"Error checking table existence: {e}")
            return False

    def get_table_columns(self, database: str, schema: str, table: str) -> List[str]:
        """Get list of column names from a Snowflake table."""
        sql = f"SHOW COLUMNS IN TABLE {database}.{schema}.{table}"
        try:
            rows = self.session.sql(sql).collect()
            return [r['column_name'] for r in rows]
        except Exception as e:
            self.logger.error(f"Error getting table columns: {e}")
            return []

    def add_missing_columns(
        self,
        database: str,
        schema: str,
        table: str,
        columns: Dict[str, str]
    ) -> None:
        """Add missing columns to an existing table."""
        existing = [c.upper() for c in self.get_table_columns(database, schema, table)]
        for col, col_type in columns.items():
            if col.upper() not in existing:
                sql = f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {col} {col_type}"
                self.logger.info(f"Adding missing column: {col} {col_type}")
                self.safe_execute(sql)

    def ensure_table(
        self,
        database: str,
        schema: str,
        table: str,
        columns_sql: Dict[str, str]
    ) -> None:
        """Create a table if it doesn't exist, or add missing columns."""
        if not self.table_exists(database, schema, table):
            cols = ",\n    ".join([f"{c} {t}" for c, t in columns_sql.items()])
            sql = f"CREATE TABLE IF NOT EXISTS {database}.{schema}.{table} (\n    {cols}\n);"
            self.logger.info(f"Creating table {database}.{schema}.{table}...")
            self.safe_execute(sql)
        else:
            self.logger.info(f"Table {database}.{schema}.{table} already exists")
            self.add_missing_columns(database, schema, table, columns_sql)

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
        if self.session:
            self.session.close()
            self.logger.info("Session closed")
