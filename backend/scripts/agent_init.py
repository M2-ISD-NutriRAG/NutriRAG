"""
Agent Initialization Script

This script executes the agent_init.sql query to create the demo agent in Snowflake.
Uses the new SQL utilities for cleaner execution.

Run this script from the backend directory with the virtual environment activated.

Usage:
    python scripts/agent_init.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utils.sql_utils import execute_sql_file


def main():
    """Main entry point."""
    try:
        print("🔧 NutriRAG Agent Initialization")
        print("=" * 50)

        sql_file = Path(__file__).parent / "agent_init.sql"
        success = execute_sql_file(sql_file, silent=False)

        if success:
            print("\n🎊 Agent initialization completed successfully!")
            print("   Your demo agent should now be available in Snowflake.")
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
