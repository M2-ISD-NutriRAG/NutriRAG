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

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string values to remove problematic characters for SQL."""
        if not isinstance(text, str):
            return text

        # Handle escaped quotes first - convert \" to simple quote
        cleaned = text.replace('\\"', "'")

        # Remove HTML tags
        import re
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)  # Replace HTML tags with spaces

        # Remove or replace problematic characters
        cleaned = cleaned.replace('\n', ' ')  # Replace newlines with spaces
        cleaned = cleaned.replace('\r', ' ')  # Replace carriage returns with spaces
        cleaned = cleaned.replace('\t', ' ')  # Replace tabs with spaces

        # Remove other control characters (ASCII 0-31 except tab, newline, carriage return which we already handled)
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in ['\t', '\n', '\r'])

        # Normalize multiple spaces to single space
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

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
        # Sanitize the string to remove problematic characters
        text = self._sanitize_string(text)
        stripped = text.strip()

        # Try to detect list/dict payloads and use ARRAY_CONSTRUCT instead of PARSE_JSON
        if (stripped.startswith("[") and stripped.endswith("]")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            # Use _format_json_array for consistency
            return self._format_json_array(value)

        # Escape single quotes for SQL string literals
        escaped = text.replace("'", "''")
        return f"'{escaped}'"

    def _format_json_array(self, value) -> str:
        """Force value to a JSON array and wrap with PARSE_JSON."""
        import json
        
        try:
            # Try JSON first for better performance
            parsed = json.loads(value) if isinstance(value, str) else value
        except (json.JSONDecodeError, TypeError):
            try:
                # Fallback to ast.literal_eval
                parsed = ast.literal_eval(value) if isinstance(value, str) else value
            except Exception:
                # If both fail, try to parse manually for common cases
                if isinstance(value, str):
                    # Handle cases like '["item1", "item2"]' that might have formatting issues
                    stripped = value.strip()
                    if stripped.startswith('[') and stripped.endswith(']'):
                        # Try to extract items manually
                        content = stripped[1:-1]  # Remove brackets
                        if content.strip():
                            # Split by comma but be careful with commas inside quotes
                            import re
                            # Split by comma not inside quotes
                            items = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', content)
                            parsed = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                        else:
                            parsed = []
                    else:
                        parsed = [value]
                else:
                    parsed = None

        if isinstance(parsed, list):
            data = parsed
        else:
            data = [value] if value is not None else []

        # Format each item as a simple value without recursion
        formatted_items = []
        for item in data:
            if pd.isna(item):
                formatted_items.append("NULL")
            elif isinstance(item, (int, float)):
                formatted_items.append(str(item))
            elif isinstance(item, bool):
                formatted_items.append("TRUE" if item else "FALSE")
            else:
                # For strings and other types, sanitize and quote
                text = str(item)
                text = self._sanitize_string(text)
                escaped = text.replace("'", "''")
                formatted_items.append(f"'{escaped}'")

        # Build ARRAY_CONSTRUCT to avoid JSON parsing issues in Snowflake
        return f"ARRAY_CONSTRUCT({', '.join(formatted_items)})"

    def generate(
        self,
        csv_path: Optional[str] = None,
        output_sql_path: Optional[str] = None,
        table_fqn: Optional[str] = None,
        batch_size: int = 1000,
        nrows: Optional[int] = None,
    ) -> str:
        """Generate an INSERT script from a CSV file.

        Args:
            csv_path: Path to source CSV. Defaults to cleaned_recipes in cache.
            output_sql_path: Where to write the SQL file.
            table_fqn: Fully qualified table name to insert into.
            batch_size: Number of rows read per chunk.
            nrows: Optional limit on the number of rows to process.

        Returns:
            Path to the generated SQL file.
        """
        csv_path = csv_path or os.path.join(self.cache_dir, OUTPUT_FILES["cleaned_recipes"])
        output_sql_path = output_sql_path or os.path.join(self.sql_dir, "clean_recipes_inserts.sql")
        table_fqn = table_fqn or f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['cleaned_table']}"

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        # Prepare column list once
        first_chunk = pd.read_csv(csv_path, nrows=0)
        columns = list(first_chunk.columns)
        # Filter out validation_errors column if it exists (not needed in Snowflake)
        columns = [c for c in columns if c.lower() != "validation_errors"]
        col_list = ", ".join(columns)  # No quotes around column names for Snowflake

        with open(output_sql_path, "w", encoding="utf-8") as out:
            for chunk in pd.read_csv(csv_path, chunksize=batch_size, nrows=nrows):
                for _, row in chunk.iterrows():
                    # Ensure DATE type uses TO_DATE for Snowflake
                    row_values = []
                    for col in columns:
                        val = row[col]
                        if isinstance(val, str) and col.lower() == "submitted":
                            # Expect YYYY-MM-DD format
                            sanitized_date = self._sanitize_string(str(val))
                            safe_date = sanitized_date.replace("'", "''")
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

    def generate_raw(
        self,
        csv_path: str,
        table_fqn: str,
        output_sql_path: str,
        batch_size: int = 1000,
        nrows: Optional[int] = None,
    ) -> str:
        """Generate INSERT statements from a raw CSV file.

        Args:
            csv_path: Path to the CSV file.
            table_fqn: Fully qualified table name.
            output_sql_path: Path to output SQL file.
            batch_size: Number of rows per chunk.
            nrows: Optional limit on the number of rows to process.

        Returns:
            Path to the generated SQL file.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        # Read first chunk to get columns
        first_chunk = pd.read_csv(csv_path, nrows=0)
        columns = list(first_chunk.columns)
        col_list = col_list = ", ".join([col.upper() for col in columns])  # No quotes around column names for Snowflake

        with open(output_sql_path, "w", encoding="utf-8") as out:
            for chunk in pd.read_csv(csv_path, chunksize=batch_size, nrows=nrows):
                for _, row in chunk.iterrows():
                    row_values = []
                    for col in columns:
                        val = row[col]
                        # Special handling for date columns
                        if col.lower() in ["submitted", "date"]:
                            if pd.notna(val):
                                sanitized_date = self._sanitize_string(str(val))
                                safe_date = sanitized_date.replace("'", "''")
                                row_values.append(f"TO_DATE('{safe_date}')")
                            else:
                                row_values.append("NULL")
                        else:
                            row_values.append(self._format_value(val))

                    # Use INSERT ... SELECT to allow function expressions in values
                    stmt = f"INSERT INTO {table_fqn} ({col_list}) SELECT {', '.join(row_values)};\n"
                    out.write(stmt)

        return output_sql_path
if __name__=="__main__":
    generator = SqlInsertGenerator()
    sql_path = generator.generate()
    print(f"SQL file generated at: {sql_path}")
