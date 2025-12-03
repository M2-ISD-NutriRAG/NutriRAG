"""
Safe ingestion script to run transformations and load results into Snowflake.

Features:
- Connects to Snowflake using a JSON config file (env `SNOWFLAKE_CONFIG`) or env vars.
- Reads raw table, applies cleaning and filter extraction (based on notebook logic).
- Safely creates target tables and columns if they don't exist.
- Writes cleaned data using `session.write_pandas` (overwrite behavior configurable).

Usage:
  export SNOWFLAKE_CONFIG=./snowflake_config.json
  python ingest_to_snowflake.py

The JSON config should contain the Snowflake connection params accepted by
`snowflake.snowpark.Session.builder.configs(...)`, e.g. {
  "account": "...",
  "user": "...",
  "password": "...",
  "role": "...",
  "warehouse": "...",
  "database": "NUTRIRAG_PROJECT",
  "schema": "RAW"
}

If `SNOWFLAKE_CONFIG` is not set, the script will attempt to read individual
environment variables: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`,
`SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`.
"""

import json
import os
import ast
from typing import Dict, List

import pandas as pd

from snowflake.snowpark import Session


def load_snowflake_config() -> Dict:
    cfg_path = os.getenv("SNOWFLAKE_CONFIG")
    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            return json.load(f)

    # fallback to environment variables
    env = os.environ
    cfg = {}
    if env.get("SNOWFLAKE_ACCOUNT"):
        cfg.update({
            "account": env.get("SNOWFLAKE_ACCOUNT"),
            "user": env.get("SNOWFLAKE_USER"),
            "password": env.get("SNOWFLAKE_PASSWORD"),
            "role": env.get("SNOWFLAKE_ROLE"),
            "warehouse": env.get("SNOWFLAKE_WAREHOUSE"),
            "database": env.get("SNOWFLAKE_DATABASE"),
        })
    return {k: v for k, v in cfg.items() if v}


def create_session_from_config(cfg: Dict) -> Session:
    if not cfg:
        raise ValueError("Snowflake config not found. Set SNOWFLAKE_CONFIG or env vars.")
    builder = Session.builder.configs(cfg)
    return builder.create()


def safe_execute(session: Session, sql: str):
    """Execute SQL and return the result; prints and continues on errors."""
    try:
        return session.sql(sql).collect()
    except Exception as e:
        print(f"SQL execution error:\n{sql}\n-> {e}")
        raise


def table_exists(session: Session, database: str, schema: str, table: str) -> bool:
    sql = f"SHOW TABLES IN {database}.{schema} LIKE '{table}'"
    try:
        res = session.sql(sql).collect()
        return len(res) > 0
    except Exception:
        # Fallback: try fully qualified name
        try:
            session.table(f"{database}.{schema}.{table}")
            return True
        except Exception:
            return False


def get_table_columns(session: Session, database: str, schema: str, table: str) -> List[str]:
    sql = f"SHOW COLUMNS IN TABLE {database}.{schema}.{table}"
    try:
        rows = session.sql(sql).collect()
        return [r['column_name'] for r in rows]
    except Exception:
        return []


def add_missing_columns(session: Session, database: str, schema: str, table: str, columns: Dict[str, str]):
    existing = [c.upper() for c in get_table_columns(session, database, schema, table)]
    for col, col_type in columns.items():
        if col.upper() not in existing:
            sql = f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {col} {col_type}"
            print(f"Adding missing column: {col} {col_type}")
            safe_execute(session, sql)


def ensure_table(session: Session, database: str, schema: str, table: str, columns_sql: Dict[str, str]):
    if not table_exists(session, database, schema, table):
        cols = ",\n    ".join([f"{c} {t}" for c, t in columns_sql.items()])
        sql = f"CREATE TABLE {database}.{schema}.{table} (\n    {cols}\n);"
        print(f"Creating table {database}.{schema}.{table}...")
        safe_execute(session, sql)
    else:
        print(f"Table {database}.{schema}.{table} already exists. Checking columns...")
        add_missing_columns(session, database, schema, table, columns_sql)


def safe_write_pandas(session: Session, df: pd.DataFrame, database: str, schema: str, table: str, overwrite: bool = True):
    # Ensure table exists with minimal schema matching DataFrame columns (simple VARCHAR fallback)
    minimal_schema = {col.upper(): "VARCHAR" for col in df.columns}
    ensure_table(session, database, schema, table, minimal_schema)

    print(f"Writing DataFrame to {database}.{schema}.{table} (overwrite={overwrite})")
    session.write_pandas(df, table_name=table, schema=schema, database=database, overwrite=overwrite)


def safe_literal_eval_list(x):
    if isinstance(x, list):
        return x
    if x is None:
        return []
    try:
        return ast.literal_eval(x)
    except Exception:
        return []

def run():
    cfg = load_snowflake_config()
    session = create_session_from_config(cfg)

    # Read raw table
    print("Reading RAW table into pandas...")
    df = session.table("NUTRIRAG_PROJECT.RAW.RAW_RECIPES_110K")
    recipes = df.to_pandas()

    # Normalize nutrition column to list
    recipes["NUTRITION"] = recipes["NUTRITION"].apply(
        lambda x: x if isinstance(x, list) else (ast.literal_eval(x) if (x is not None and x != "") else [])
    )

    # Apply filters from notebook
    clean_data = recipes[
        (recipes["NAME"].notna()) &
        (recipes["NAME"].apply(lambda x: len(x) > 0)) &
        (recipes["MINUTES"] > 5) &
        (recipes["ID"].notna()) &
        (recipes["SUBMITTED"].notna()) &
        (recipes["TAGS"].apply(lambda x: len(safe_literal_eval_list(x)) > 0)) &
        (recipes["NUTRITION"].apply(lambda x: len(x) == 7)) &
        (recipes["DESCRIPTION"].notna()) &
        (recipes["STEPS"].apply(lambda x: len(safe_literal_eval_list(x)) > 0)) &
        (recipes["INGREDIENTS"].apply(lambda x:  len(safe_literal_eval_list(x)) > 0))
    ]

    # Sample 50k
    clean_data = clean_data.sample(n=50000, random_state=42).reset_index(drop=True)

    # Define table column specifications (simple types) for CLEANED.RECIPES_SAMPLE_50K
    columns_spec = {
        "NAME": "VARCHAR(16777216)",
        "ID": "NUMBER(38,0)",
        "MINUTES": "NUMBER(38,0)",
        "CONTRIBUTOR_ID": "NUMBER(38,0)",
        "SUBMITTED": "TIMESTAMP_NTZ",
        "TAGS": "ARRAY",
        "NUTRITION": "ARRAY",
        "N_STEPS": "NUMBER(38,0)",
        "STEPS": "ARRAY",
        "DESCRIPTION": "VARCHAR(16777216)",
        "INGREDIENTS": "ARRAY",
        "N_INGREDIENTS": "NUMBER(38,0)",
        "HAS_IMAGE": "NUMBER(38,0)",
        "IMAGE_URL": "VARCHAR(16777216)",
        "INGREDIENTS_RAW_STR": "ARRAY",
        "SERVING_SIZE": "NUMBER(38,0)",
        "SERVINGS": "NUMBER(38,0)",
        "SEARCH_TERMS": "ARRAY",
        "FILTERS": "ARRAY",
    }

    # Ensure cleaned table exists and write (overwrite)
    ensure_table(session, "NUTRIRAG_PROJECT", "CLEANED", "RECIPES_SAMPLE_50K", columns_spec)
    safe_write_pandas(session, clean_data, "NUTRIRAG_PROJECT", "CLEANED", "RECIPES_SAMPLE_50K", overwrite=True)

    # Also write DEV_SAMPLE.RECIPES_SAMPLE_50K (smaller sample)
    # dev_data = clean_data.sample(n=1000, random_state=42).reset_index(drop=True)
    ensure_table(session, "NUTRIRAG_PROJECT", "DEV_SAMPLE", "RECIPES_SAMPLE_50K", columns_spec)
    safe_write_pandas(session, clean_data, "NUTRIRAG_PROJECT", "DEV_SAMPLE", "RECIPES_SAMPLE_50K", overwrite=True)

    # Create a STR table (stringified arrays) as in notebook
    print("Creating stringified version of the cleaned table (RECIPES_SAMPLE_50K_STR)")
    str_table_sql = (
        "CREATE OR REPLACE TABLE NUTRIRAG_PROJECT.CLEANED.RECIPES_SAMPLE_50K_STR AS "
        "SELECT id, name, minutes, contributor_id, submitted, "
        "ARRAY_TO_STRING(tags, ' | ') AS tags_text, "
        "ARRAY_TO_STRING(ingredients, ' | ') AS ingredients_text, "
        "ARRAY_TO_STRING(nutrition, ' | ') AS nutrition_text, "
        "ARRAY_TO_STRING(steps, ' | ') AS steps_text, "
        "description, n_ingredients, n_steps "
        "FROM NUTRIRAG_PROJECT.CLEANED.RECIPES_SAMPLE_50K"
    )
    safe_execute(session, str_table_sql)

    # Add separated nutrition columns if they don't exist
    nutrition_cols = {
        "CALORIES": "FLOAT",
        "TOTAL_FAT": "FLOAT",
        "SUGAR": "FLOAT",
        "SODIUM": "FLOAT",
        "PROTEIN": "FLOAT",
        "SATURATED_FAT": "FLOAT",
        "CARBS": "FLOAT",
    }
    ensure_table(session, "NUTRIRAG_PROJECT", "CLEANED", "RECIPES_SAMPLE_50K_STR", {
        # minimal columns to ensure table exists; existing table was created above
        "ID": "NUMBER(38,0)",
        "NAME": "VARCHAR(16777216)",
    })
    add_missing_columns(session, "NUTRIRAG_PROJECT", "CLEANED", "RECIPES_SAMPLE_50K_STR", nutrition_cols)

    # Update nutrition columns from nutrition array
    update_sql = (
        "UPDATE NUTRIRAG_PROJECT.CLEANED.RECIPES_SAMPLE_50K_STR SET "
        "CALORIES = SPLIT_PART(nutrition_text, ' | ', 1)::FLOAT, "
        "TOTAL_FAT = SPLIT_PART(nutrition_text, ' | ', 2)::FLOAT, "
        "SUGAR = SPLIT_PART(nutrition_text, ' | ', 3)::FLOAT, "
        "SODIUM = SPLIT_PART(nutrition_text, ' | ', 4)::FLOAT, "
        "PROTEIN = SPLIT_PART(nutrition_text, ' | ', 5)::FLOAT, "
        "SATURATED_FAT = SPLIT_PART(nutrition_text, ' | ', 6)::FLOAT, "
        "CARBS = SPLIT_PART(nutrition_text, ' | ', 7)::FLOAT"
    )
    # Use try/except because nutrition_text might not exist in some schemas
    try:
        safe_execute(session, update_sql)
    except Exception as e:
        print(f"Could not update nutrition columns: {e}")

    print("Ingestion finished.")


if __name__ == "__main__":
    run()