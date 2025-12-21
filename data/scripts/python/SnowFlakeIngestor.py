import ast
import logging

from config import DATA_PARAMS, SNOWFLAKE_CONFIG
from DataTransformer import DataTransformer
from SnowflakeConnector import SnowflakeConnector

class SnowflakeIngestor:
    """Orchestrates the ingestion process into Snowflake."""

    def __init__(self, connector: SnowflakeConnector, transformer: DataTransformer):
        self.connector = connector
        self.transformer = transformer
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_ingestion(self):
        # Read raw table
        self.logger.info("Reading RAW table into pandas...")
        table_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['raw_table']}"
        df = self.connector.session.table(table_path)
        recipes = df.to_pandas()

        # Normalize nutrition
        recipes["NUTRITION"] = recipes["NUTRITION"].apply(
            lambda x: x if isinstance(x, list) else (ast.literal_eval(x) if (x is not None and x != "") else [])
        )

        # Apply filters (simplified from notebook)
        clean_data = recipes[
            (recipes["NAME"].notna()) &
            (recipes["NAME"].apply(lambda x: len(x) > 0)) &
            (recipes["MINUTES"] > DATA_PARAMS["min_minutes"]) &
            (recipes["ID"].notna()) &
            (recipes["SUBMITTED"].notna()) &
            (recipes["TAGS"].apply(lambda x: len(self.transformer.safe_parse_list(x)) > 0)) &
            (recipes["NUTRITION"].apply(lambda x: len(x) == 7)) &
            (recipes["DESCRIPTION"].notna()) &
            (recipes["STEPS"].apply(lambda x: len(self.transformer.safe_parse_list(x)) > 0)) &
            (recipes["INGREDIENTS"].apply(lambda x: len(self.transformer.safe_parse_list(x)) > 0))
        ]

        row_count = len(clean_data)
        if row_count == 0:
            raise ValueError("No rows remain after filtering; cannot sample or ingest.")

        # Sample 50k (or all rows if fewer)
        sample_size = min(DATA_PARAMS["sample_size"], row_count)
        clean_data = clean_data.sample(n=sample_size, random_state=DATA_PARAMS["random_seed"]).reset_index(drop=True)

        # Extract filters (placeholder)
        clean_data["FILTERS"] = clean_data["TAGS"].apply(lambda x: [])  # Simplified

        # Define table schema
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

        # Write to CLEANED
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(clean_data, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        # Write dev sample (cap at available rows)
        dev_sample_size = min(DATA_PARAMS["dev_sample_size"], len(clean_data))
        dev_data = clean_data.sample(n=dev_sample_size, random_state=DATA_PARAMS["random_seed"]).reset_index(drop=True)
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(dev_data, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        self.logger.info("Ingestion finished.")