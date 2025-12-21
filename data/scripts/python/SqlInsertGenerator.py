"""
Utility to generate SQL insert statements from the cleaned recipes CSV
so the data can be inserted into Snowflake without relying on write_pandas.
"""

import ast
import json
import os
from typing import Optional

import pandas as pd

from config import CACHE_DIR, OUTPUT_FILES, SNOWFLAKE_CONFIG,SQL_DIR


class SqlInsertGenerator:
    """Generate INSERT statements for a CSV file."""

    def __init__(self, cache_dir: str = CACHE_DIR, sql_dir: str = SQL_DIR):
        self.cache_dir = cache_dir
        self.sql_dir=sql_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _format_value(self, value) -> str:
        """Format a single value for SQL INSERT."""
        if pd.isna(value):
            return "NULL"

        # Numbers and booleans can pass through
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"

        text = str(value)
        stripped = text.strip()

        # Try to detect list/dict payloads and serialize as JSON (for ARRAY/VARIANT columns)
        if (stripped.startswith("[") and stripped.endswith("]")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            try:
                parsed = ast.literal_eval(stripped)
                json_str = json.dumps(parsed)
                json_str = json_str.replace("'", "''")
                # Use SELECT-compatible expression
                return f"PARSE_JSON('{json_str}')"
            except Exception:
                # Fallback to quoted string
                pass

        # Escape single quotes for SQL string literals
        escaped = text.replace("'", "''")
        return f"'{escaped}'"

    def _format_json_array(self, value) -> str:
        """Force value to a JSON array and wrap with PARSE_JSON."""
        try:
            parsed = ast.literal_eval(value) if isinstance(value, str) else value
        except Exception:
            parsed = None

        if isinstance(parsed, list):
            data = parsed
        else:
            data = [value]

        normalized = []
        for item in data:
            if isinstance(item, str):
                cleaned = item.replace("\r", " ").replace("\n", " ")
                normalized.append(cleaned)
            else:
                normalized.append(item)

        # Build ARRAY_CONSTRUCT to avoid JSON parsing issues in Snowflake
        formatted_items = [self._format_value(item) for item in normalized]
        return f"ARRAY_CONSTRUCT({', '.join(formatted_items)})"

    def generate(
        self,
        csv_path: Optional[str] = None,
        output_sql_path: Optional[str] = None,
        table_fqn: Optional[str] = None,
        batch_size: int = 1000,
    ) -> str:
        """Generate an INSERT script from a CSV file.

        Args:
            csv_path: Path to source CSV. Defaults to cleaned_recipes in cache.
            output_sql_path: Where to write the SQL file.
            table_fqn: Fully qualified table name to insert into.
            batch_size: Number of rows read per chunk.

        Returns:
            Path to the generated SQL file.
        """
        csv_path = csv_path or os.path.join(self.cache_dir, OUTPUT_FILES["cleaned_recipes"])
        output_sql_path = output_sql_path or os.path.join(self.sql_dir, "clean_recipes_inserts.sql")
        table_fqn = table_fqn or f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['cleaned_schema']}.{SNOWFLAKE_CONFIG['cleaned_table']}"

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        # Prepare column list once
        first_chunk = pd.read_csv(csv_path, nrows=0)
        columns = list(first_chunk.columns)
        # Filter out validation_errors column if it exists (not needed in Snowflake)
        columns = [c for c in columns if c.lower() != "validation_errors"]
        col_list = ", ".join(columns)  # No quotes around column names for Snowflake

        with open(output_sql_path, "w", encoding="utf-8") as out:
            for chunk in pd.read_csv(csv_path, chunksize=batch_size,nrows=6):
                for _, row in chunk.iterrows():
                    # Ensure DATE type uses TO_DATE for Snowflake
                    row_values = []
                    for col in columns:
                        val = row[col]
                        if isinstance(val, str) and col.lower() == "submitted":
                            # Expect YYYY-MM-DD format
                            safe_date = str(val).replace("'", "''")
                            row_values.append("TO_DATE('{}')".format(safe_date))
                        elif col.lower() in {"tags", "nutrition", "steps", "ingredients", "ingredients_raw_str", "search_terms"}:
                            row_values.append(self._format_json_array(val))
                        else:
                            row_values.append(self._format_value(val))

                    # Use INSERT ... SELECT to allow function expressions in values
                    stmt = (
                        f"INSERT INTO {table_fqn} ({col_list}) SELECT {', '.join(row_values)};\n"
                    )
                    out.write(stmt)

        return output_sql_path


if __name__ == "__main__":
    generator = SqlInsertGenerator()
    sql_path = generator.generate()
    print(f"SQL file generated at: {sql_path}")
