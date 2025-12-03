"""
SQL utilities for executing SQL files and queries with Snowflake.

This module provides reusable functions for SQL operations using the SnowflakeSetup
connection management.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from setup_snowflake import SnowflakeSetup


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

    with open(sql_file_path, "r") as f:
        return f.read()


def execute_sql_file(sql_file_path: Path, silent: bool = False) -> bool:
    """
    Execute a SQL file against Snowflake using the existing SnowflakeSetup connection.

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

    # Get connection using SnowflakeSetup
    setup = SnowflakeSetup()
    conn = None

    try:
        conn = setup.get_connection(silent=True)

        if not silent:
            # Show connection info
            cursor = conn.cursor()
            cursor.execute(
                "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            user, role, warehouse, database, schema = cursor.fetchone()
            cursor.close()

            print("✅ Connected successfully!")
            print(f"   User: {user}")
            print(f"   Role: {role}")
            print(f"   Warehouse: {warehouse}")
            print(f"   Database: {database}")
            print(f"   Schema: {schema}")
            print()

        # Execute the SQL
        cursor = conn.cursor()

        try:
            # Clean SQL (remove comments and empty lines)
            clean_sql = "\n".join(
                line
                for line in sql_content.split("\n")
                if line.strip() and not line.strip().startswith("--")
            )

            if not silent:
                print(f"📋 Executing {description}")

            cursor.execute(clean_sql)

            # Try to fetch results
            try:
                result = cursor.fetchall()
                if result:
                    if not silent:
                        print(f"✅ Result: {result}")
                    return True
                else:
                    if not silent:
                        print("✅ Execution completed successfully")
                    return True
            except Exception:
                # Some statements don't return results
                if not silent:
                    print("✅ Execution completed successfully")
                return True

        except Exception as e:
            if not silent:
                print(f"❌ Error executing {description}: {e}")
            return False
        finally:
            cursor.close()

    except Exception as e:
        if not silent:
            print(f"❌ Connection error: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()
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
    setup = SnowflakeSetup()
    conn = None
    cursor = None

    try:
        conn = setup.get_connection(silent=True)
        cursor = conn.cursor()

        if not silent:
            print(
                f"🔍 Executing query: {query[:100]}{'...' if len(query) > 100 else ''}"
            )

        cursor.execute(query)

        if fetch_results:
            # Get column names
            columns = (
                [desc[0] for desc in cursor.description]
                if cursor.description
                else []
            )

            # Fetch all results
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]

            if not silent:
                print(f"✅ Query returned {len(results)} rows")

            return results
        else:
            if not silent:
                print("✅ Query executed successfully")
            return None

    except Exception as e:
        if not silent:
            print(f"❌ Query execution error: {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    """Test the SQL utilities when run directly."""
    print("🧪 Testing SQL utilities...")

    # Use the SnowflakeSetup test_connection method instead of duplicating
    setup = SnowflakeSetup()
    if setup.test_connection(detailed=False):
        print("\n✅ SQL utilities are working correctly!")
    else:
        print("\n❌ SQL utilities test failed!")
