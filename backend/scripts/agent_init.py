"""
Agent Initialization Script

This script loads environment variables from .env, replaces placeholders in agent_init.sql,
and then executes it to create the agent in Snowflake.

Run this script from the backend directory with the virtual environment activated.

Usage:
    python scripts/agent_init.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utils.sql_utils import execute_sql_file


def main():
    """Main entry point."""
    try:
        print("🔧 NutriRAG Agent Initialization")
        print("=" * 70)

        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(env_path)

        # Get configuration from .env
        snowflake_database = os.getenv("SNOWFLAKE_DATABASE")
        snowflake_services_schema = os.getenv("SNOWFLAKE_SERVICES_SCHEMA")
        snowflake_warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        agent_name = os.getenv("AGENT_NAME")

        # Build full agent name
        agent_full_name = f"{snowflake_database}.{snowflake_services_schema}.{agent_name}"

        print(f"📦 Database: {snowflake_database}")
        print(f"📦 Schema: {snowflake_services_schema}")
        print(f"🤖 Agent Name: {agent_name}")
        print(f"⚙️  Warehouse: {snowflake_warehouse}")
        print(f"✅ Full Agent Name: {agent_full_name}")
        print("=" * 70)

        # Read SQL file
        sql_file = Path(__file__).parent / "agent_init.sql"
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Replace hardcoded agent name with the one from .env
        original_agent = "NUTRIRAG_PROJECT.SERVICES.AGENT_TEST_3"
        if original_agent in sql_content:
            sql_content = sql_content.replace(original_agent, agent_full_name)
            print(f"\n✓ Replaced '{original_agent}' → '{agent_full_name}'")
        else:
            print(f"\n⚠️  Warning: Original agent name '{original_agent}' not found in SQL")

        # Replace hardcoded warehouse name (NUTRIRAG_PROJECT_VAR) with the one from .env
        original_warehouse = "NUTRIRAG_PROJECT_VAR"
        if original_warehouse in sql_content:
            sql_content = sql_content.replace(original_warehouse, snowflake_warehouse)
            print(f"✓ Replaced warehouse '{original_warehouse}' → '{snowflake_warehouse}'")
        else:
            print(f"⚠️  Warning: Original warehouse name '{original_warehouse}' not found in SQL")

        # Replace hardcoded search tool identifier with the one from .env
        original_search_tool = "NUTRIRAG_PROJECT.SERVICES.SEARCH_SIMILAR_RECIPES_TOOL"
        search_tool_full = f"{snowflake_database}.{snowflake_services_schema}.SEARCH_SIMILAR_RECIPES_TOOL"
        if original_search_tool in sql_content:
            sql_content = sql_content.replace(original_search_tool, search_tool_full)
            print(f"✓ Replaced search tool '{original_search_tool}' → '{search_tool_full}'")
        else:
            print(f"⚠️  Warning: Original search tool identifier '{original_search_tool}' not found in SQL")

        # Replace hardcoded transform tool identifier with the one from .env
        original_transform_tool = "NUTRIRAG_PROJECT.SERVICES.TRANSFORM_RECIPE"
        transform_tool_full = f"{snowflake_database}.{snowflake_services_schema}.TRANSFORM_RECIPE"
        if original_transform_tool in sql_content:
            sql_content = sql_content.replace(original_transform_tool, transform_tool_full)
            print(f"✓ Replaced transform tool '{original_transform_tool}' → '{transform_tool_full}'")
        else:
            print(f"⚠️  Warning: Original transform tool identifier '{original_transform_tool}' not found in SQL")

        # Save processed SQL temporarily
        processed_sql_file = sql_file.parent / "agent_init_processed.sql"
        with open(processed_sql_file, "w", encoding="utf-8") as f:
            f.write(sql_content)

        print(f"✓ Processed SQL saved to: {processed_sql_file}")

        # Execute processed SQL
        print("\n⏳ Executing SQL...")
        success = execute_sql_file(processed_sql_file, silent=False)

        if success:
            print("\n🎊 Agent initialization completed successfully!")
            print(f"   Agent '{agent_full_name}' is now available in Snowflake.")
            return 0
        else:
            print("\n💥 Agent initialization failed!")
            return 1

    except FileNotFoundError as e:
        print(f"❌ File error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
