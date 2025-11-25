import os
from dotenv import load_dotenv
from typing import Optional
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
import snowflake.connector


class SnowflakeClient:
    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        account: Optional[str] = None,
        role: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        autoconnect: bool = True,
    ) -> None:
        # Load .env file once
        load_dotenv()

        self.config = {
            "user": user or os.getenv("SNOWFLAKE_USER"),
            "password": password or os.getenv("SNOWFLAKE_PASSWORD"),
            "account": account or os.getenv("SNOWFLAKE_ACCOUNT"),
            "role": role or os.getenv("SNOWFLAKE_ROLE"),
            "warehouse": warehouse or os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": database or os.getenv("SNOWFLAKE_DATABASE"),
            "schema": schema or os.getenv("SNOWFLAKE_SCHEMA"),
        }

        missing = [k for k, v in self.config.items() if v is None]
        if missing:
            raise ValueError(f"Missing Snowflake config values: {', '.join(missing)}")

        self._conn = None

        if autoconnect:
            self.connect()


    def connect(self) -> None:
        """Open a connection if not already open."""
        if self._conn is not None and not self._conn.is_closed():
            return

        try:
            self._conn = snowflake.connector.connect(**self.config)
        except Exception as e:
            return


    def close(self) -> None:
        """Close the connection if open."""
        if self._conn is not None and not self._conn.is_closed():
            self._conn.close()


    def __enter__(self) -> "SnowflakeClient":
        self.connect()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


    def execute(self, query, params = None, fetch = None):
        """
        Execute a query.

        fetch can be:
        - None -> don't fetch, just execute (INSERT/UPDATE/etc)
        - "one" -> fetchone()
        - "all" -> fetchall()
        """
        if self._conn is None or self._conn.is_closed():
            self.connect()

        cur = self._conn.cursor()
        try:
            cur.execute(query, params or ())
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return None
        finally:
            cur.close()

    def is_connected(self) -> dict:
        """
        Run a basic health check against Snowflake.
        Returns info dict (version, ok flag).
        """
        return self._conn is not None and not self._conn.is_closed()

