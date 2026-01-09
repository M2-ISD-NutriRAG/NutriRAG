"""
SQL utilities for executing SQL files and queries with Snowflake.

This module provides reusable functions for SQL operations using the SnowflakeClient
connection management.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.snowflake.client import SnowflakeClient


def load_sql_file(sql_file_path: Path) -> str:
    """
    Load SQL content from file.
    # TODO: add jinja2 templating support to pass parameters in sql files

    Args:
        sql_file_path: Path to the SQL file

    Returns:
        SQL content as string

    Raises:
        FileNotFoundError: If SQL file doesn't exist
    """
    if not sql_file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as f:
        return f.read()


def execute_sql_file(sql_file_path: Path, silent: bool = False) -> bool:
    """
    Execute a SQL file against Snowflake using the SnowflakeClient.

    Args:
        sql_file_path: Path to the SQL file to execute
        silent: If True, suppress verbose output

    Returns:
        True if execution successful, False otherwise

    Raises:
        FileNotFoundError: If SQL file doesn't exist
        Exception: If connection or execution fails
    """
    if not sql_file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

    # Read SQL content using existing function
    sql_content = load_sql_file(sql_file_path)

    return execute_sql_content(sql_content, sql_file_path.name, silent)


def execute_sql_content(
    sql_content: str, description: str = "SQL", silent: bool = False
) -> bool:
    """
    Execute SQL content against Snowflake.

    Args:
        sql_content: The SQL content to execute
        description: Description of what's being executed (for logging)
        silent: If True, suppress verbose output

    Returns:
        True if execution successful, False otherwise
    """
    if not silent:
        print(f"🚀 Executing {description}...")
        print("📝 Content preview (first 200 chars):")
        print(f"   {sql_content[:200]}...")
        print()

    try:
        with SnowflakeClient() as client:
            if not silent:
                # Show connection info
                conn_info = client.execute(
                    "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()",
                    fetch="one",
                )
                if conn_info:
                    user, role, warehouse, database, schema = conn_info
                    print("✅ Connected successfully!")
                    print(f"   User: {user}")
                    print(f"   Role: {role}")
                    print(f"   Warehouse: {warehouse}")
                    print(f"   Database: {database}")
                    print(f"   Schema: {schema}")
                    print()

            # Clean SQL (remove empty lines and full-line comments only)
            # Only removes lines that are purely comments (start with -- after whitespace)
            # Preserves inline comments and -- within strings
            lines = []
            for line in sql_content.split("\n"):
                stripped = line.strip()
                if stripped and not stripped.startswith("--"):
                    lines.append(line)  # Keep original line with indentation
            clean_sql = "\n".join(lines)

            if not silent:
                print(f"📋 Executing {description}")

            # Execute the SQL - let the client handle whether to fetch results or not
            result = client.execute(clean_sql)
            if result:
                if not silent:
                    print(f"✅ Result: {result}")
            else:
                if not silent:
                    print("✅ Execution completed successfully")
            return True

    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")
        return False

    finally:
        if not silent:
            print("🔌 Connection closed")


def execute_sql_query(
    query: str, fetch_results: bool = True, silent: bool = False
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a single SQL query and optionally return results.

    Args:
        query: The SQL query to execute
        fetch_results: If True, fetch and return results
        silent: If True, suppress output

    Returns:
        Query results as list of dictionaries if fetch_results=True, None otherwise
    """
    try:
        with SnowflakeClient() as client:
            if not silent:
                print(
                    f"🔍 Executing query: {query[:100]}{'...' if len(query) > 100 else ''}"
                )

            if fetch_results:
                # Use client's execute method to fetch results
                result = client.execute(query, fetch="all")

                # Convert to list of dictionaries if we have results
                if result:
                    if not silent:
                        print(f"✅ Query returned {len(result)} rows")

                    # Convert tuples to list of dictionaries
                    results = []
                    for row in result:
                        if isinstance(row, (list, tuple)):
                            # For now, create generic column names
                            columns = [f"col_{i}" for i in range(len(row))]
                            results.append(dict(zip(columns, row)))
                        else:
                            # Single value result
                            results.append({"col_0": row})

                    return results
                else:
                    if not silent:
                        print("✅ Query returned 0 rows")
                    return []
            else:
                # Execute without fetching results
                client.execute(query)
                if not silent:
                    print("✅ Query executed successfully")
                return None

    except Exception as e:
        print(f"❌ Query execution error: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    """Test the SQL utilities when run directly."""
    print("🧪 Testing SQL utilities...")

    # Test with SnowflakeClient
    try:
        with SnowflakeClient() as client:
            result = client.execute(
                "SELECT CURRENT_VERSION(), CURRENT_USER()", fetch="one"
            )
            if result:
                print(f"✅ Connected as {result[1]} (Snowflake {result[0]})")
                success = True
            else:
                print("❌ Connection test failed: No result returned")
                success = False
    except Exception as e:
        print(f"❌ Connection test failed: {type(e).__name__}: {e}")
        success = False

    if success:
        print("\n✅ SQL utilities are working correctly!")
    else:
        print("\n❌ SQL utilities test failed!")
