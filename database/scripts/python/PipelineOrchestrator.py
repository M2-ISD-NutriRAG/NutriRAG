"""
Pipeline Orchestrator for NutriRAG data processing.

Manages the complete data pipeline orchestration with clean separation of concerns.
Each phase is handled through dedicated methods that coordinate with existing classes.
"""

import logging
import os
from typing import Optional

import pandas as pd

from DataTransformer import DataTransformer
from SnowflakeUtils import SnowflakeUtils
from CleanData import CleanData
import generate_schema
from config import (
    OUTPUT_FILES,
    SNOWFLAKE_CONFIG,
    CACHE_DIR,
    SQL_DIR
)


class PipelineOrchestrator:
    """Orchestrates the complete NutriRAG data pipeline."""

    def __init__(self):
        """Initialize the orchestrator with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.connector: Optional[SnowflakeUtils] = None

    def phase_0_setup_schema(self, connector: SnowflakeUtils) -> None:
        """
        PHASE 0: Create Snowflake schema and tables from schema_db.sql.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 0: SNOWFLAKE SCHEMA SETUP")
        self.logger.info("=" * 60)

        try:
            # Get the path to schema_db.sql
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_file = os.path.join(script_dir, "..", "sql", "schema_db_generated.sql")

            if not os.path.exists(schema_file):
                raise FileNotFoundError(f"Schema file not found: {schema_file}")

            self.logger.info(f"Reading schema from: {schema_file}")

            # Read and execute SQL file
            with open(schema_file, "r") as f:
                sql_content = f.read()

            # Split by semicolon and clean statements
            statements = self._parse_sql_statements(sql_content)
            self.logger.info(f"Found {len(statements)} SQL statements (after filtering comments)")

            for idx, statement in enumerate(statements, 1):
                try:
                    self.logger.info(f"Executing statement {idx}/{len(statements)}...")
                    stmt_preview = statement[:80].replace("\n", " ")
                    self.logger.debug(f"Statement: {stmt_preview}...")

                    connector.safe_execute(statement)
                    self.logger.info(f"✅ Statement {idx} executed")
                except Exception as e:
                    self.logger.error(f"❌ Error on statement {idx}: {e}")
                    self.logger.error(f"Statement: {statement[:200]}")
                    raise

            self.logger.info("✅ Snowflake schema setup complete")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Schema setup failed: {e}", exc_info=True)
            raise

    def phase_1c_load_raw_data(self, connector: SnowflakeUtils, nrows) -> None:
        """
        PHASE 1C: Fast load raw data directly to Snowflake via write_pandas.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 1C: FAST LOAD RAW DATA (WRITE_PANDAS)")
        self.logger.info("=" * 60)

        load_tasks = [
            # ("ingredients_parsing", SNOWFLAKE_CONFIG['raw_schema'], SNOWFLAKE_CONFIG['ingredients_parsing_table']),
            # TODO: ici rajouter le fichier csv de parsing
            ("raw_recipes", SNOWFLAKE_CONFIG['raw_schema'], SNOWFLAKE_CONFIG['raw_table']),
            ("raw_interactions", SNOWFLAKE_CONFIG['raw_schema'], "RAW_INTERACTION_10K"),
            # ("cleaned_ingredients", SNOWFLAKE_CONFIG['raw_schema'], "CLEANED_INGREDIENTS"),
            ("recipes_images", SNOWFLAKE_CONFIG['raw_schema'], "RECIPES_ENHANCED_V2"),
            ("recipes_w_search_terms", SNOWFLAKE_CONFIG['raw_schema'], "RECIPES_W_SEARCH_TERMS"),
            ("ingredients_with_clusters", SNOWFLAKE_CONFIG['analytics_schema'], SNOWFLAKE_CONFIG['ingredients_with_clusters_table']),
        ]

        try:
            for file_key, schema, table_name in load_tasks:
                csv_filename = OUTPUT_FILES.get(file_key)
                if not csv_filename:
                    continue

                csv_path = os.path.join(CACHE_DIR, csv_filename)
                if not os.path.exists(csv_path):
                    self.logger.warning(f"CSV not found: {csv_path}, skipping")
                    continue

                self.logger.info(f"🚀 Fast loading {csv_filename} to {schema}.{table_name}...")

                df = pd.read_csv(csv_path,nrows=nrows)

                # Clean CLEANED_INGREDIENTS (numeric errors)
                if file_key == "cleaned_ingredients":
                    self.logger.info(f"🧹 Cleaning numeric columns for {file_key}...")
                    for col in df.columns:
                        if col.lower() not in ['descrip', 'ndb_no']:
                            df[col] = pd.to_numeric(df[col], errors='coerce')

                # Clean RECIPES_W_SEARCH_TERMS (JSON/Set format)
                if file_key == "recipes_w_search_terms":
                    self.logger.info(f"🧹 Fixing JSON format for {file_key}...")
                    if "search_terms" in df.columns:
                        df["search_terms"] = (
                            df["search_terms"]
                            .astype(str)
                            .str.replace('{', '[')
                            .str.replace('}', ']')
                        )
                    if "tags" in df.columns:
                        df["tags"] = (
                            df["tags"]
                            .astype(str)
                            .str.replace('{', '[')
                            .str.replace('}', ']')
                        )

                # Uppercase columns
                df.columns = [c.upper() for c in df.columns]

                # Load to Snowflake
                connector.write_pandas(
                    df=df,
                    database=SNOWFLAKE_CONFIG['database'],
                    schema=schema,
                    table=table_name,
                    overwrite=True,
                    auto_create_table=True
                )

                self.logger.info(f"✅ Successfully loaded {table_name}")

        except Exception as e:
            self.logger.error(f"Fast load failed: {e}", exc_info=True)
            raise

    def phase_3_ingest_data(self, connector: SnowflakeUtils) -> None:
        """
        PHASE 3: Ingest data into Snowflake (server-side SQL).
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 3: SNOWFLAKE INGESTION (SERVER-SIDE)")
        self.logger.info("=" * 60)

        try:
            transformer = DataTransformer()
            ingestor = CleanData(connector, transformer)

            # Use server-side SQL ingestion for better performance
            ingestor.run_ingestion_sql()

            self.logger.info("✅ Data ingestion complete")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise

    def nutri_score(self, connector: SnowflakeUtils) -> None:
        """
        Calculate nutritional scores by executing nutri_score.sql.
        """
        self.logger.info("=" * 60)
        self.logger.info("CALCULATING NUTRITION SCORES")
        self.logger.info("=" * 60)

        try:
            nutri_score_path = os.path.join(SQL_DIR, "nutri_score.sql")
            if not os.path.exists(nutri_score_path):
                raise FileNotFoundError(f"Nutrition score SQL file not found: {nutri_score_path}")

            self.logger.info(f"Reading SQL from: {nutri_score_path}")
            with open(nutri_score_path, "r", encoding="utf-8") as f:
                sql_template = f.read()
            
            # Replace placeholders with actual config values
            sql = sql_template.format(
                database=SNOWFLAKE_CONFIG['database'],
                raw_schema=SNOWFLAKE_CONFIG['raw_schema'],
                cleaned_schema=SNOWFLAKE_CONFIG['cleaned_schema'],
                enriched_schema=SNOWFLAKE_CONFIG.get('enriched_schema', 'ENRICHED')
            )

            # Split into statements and execute
            statements = self._parse_sql_statements(sql)
            self.logger.info(f"Found {len(statements)} SQL statements to execute")

            for idx, statement in enumerate(statements, 1):
                try:
                    self.logger.info(f"Executing statement {idx}/{len(statements)}...")
                    stmt_preview = statement[:100].replace("\n", " ")
                    self.logger.debug(f"Statement: {stmt_preview}...")

                    connector.safe_execute(statement)
                    self.logger.info(f"✅ Statement {idx} completed")
                except Exception as e:
                    self.logger.error(f"❌ Error on statement {idx}: {e}")
                    self.logger.error(f"Statement: {statement[:200]}")
                    raise

            self.logger.info("✅ Nutrition score calculation completed successfully!")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Nutrition score calculation failed: {e}", exc_info=True)
            raise

    def extract_filters(self, connector: SnowflakeUtils) -> None:
        """
        Extract dietary filters from recipe tags and populate FILTERS column.
        
        Creates a UDF that maps tags to filter categories (vegan, vegetarian, 
        kosher, dairy-free, gluten-free, etc.) and updates RECIPES_SAMPLE_50K.
        """
        self.logger.info("=" * 60)
        self.logger.info("EXTRACTING DIETARY FILTERS FROM TAGS")
        self.logger.info("=" * 60)

        try:
            filters_path = os.path.join(SQL_DIR, "extract_filters_udf.sql")
            if not os.path.exists(filters_path):
                raise FileNotFoundError(f"Filters SQL file not found: {filters_path}")

            self.logger.info(f"Reading SQL from: {filters_path}")
            with open(filters_path, "r", encoding="utf-8") as f:
                sql_template = f.read()

            # Replace variables with config values
            sql_content = sql_template.format(
                database=SNOWFLAKE_CONFIG['database'],
                raw_schema=SNOWFLAKE_CONFIG['raw_schema'],
                raw_table=SNOWFLAKE_CONFIG['raw_table'],
                cleaned_schema=SNOWFLAKE_CONFIG['cleaned_schema'],
                cleaned_table=SNOWFLAKE_CONFIG['cleaned_table']
            )

            # Split by semicolon but preserve line breaks (Python UDF needs proper indentation)
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            self.logger.info(f"Found {len(statements)} SQL statements to execute")

            for idx, statement in enumerate(statements, 1):
                try:
                    self.logger.info(f"Executing statement {idx}/{len(statements)}...")
                    stmt_preview = statement[:100].replace("\n", " ")
                    self.logger.debug(f"Statement: {stmt_preview}...")

                    connector.safe_execute(statement)
                    self.logger.info(f"✅ Statement {idx} completed")
                except Exception as e:
                    self.logger.error(f"❌ Error on statement {idx}: {e}")
                    self.logger.error(f"Statement: {statement[:200]}")
                    raise

            self.logger.info("✅ Filters extraction completed successfully!")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Filters extraction failed: {e}", exc_info=True)
            raise

    def run_full_pipeline(self, nrows: Optional[int] = None) -> None:
        """
        Run the complete data pipeline with a single Snowflake connection.
        
        Args:
            nrows: Optional limit on number of rows to process
        """
        connector = SnowflakeUtils()
        try:
            self.phase_0_setup_schema(connector) # create snowflake schema
            self.phase_1c_load_raw_data(connector, nrows) # fast load to snowflake
            self.extract_filters(connector) # extract dietary filters from tags
            self.phase_3_ingest_data(connector) # generate clean data to save to snowflake
            # self.nutri_score(connector) # calculate nutrition scores
            self.logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            raise
        finally:
            connector.close()
            self.logger.info("✅ Snowflake connection closed")

    @staticmethod
    def _parse_sql_statements(sql_content: str) -> list:
        """
        Parse SQL statements from content, handling comments.
        
        Args:
            sql_content: Raw SQL file content
            
        Returns:
            List of cleaned SQL statements
        """
        statements = []
        for stmt in sql_content.split(";"):
            stmt = stmt.strip()

            lines = []
            for line in stmt.split("\n"):
                line = line.strip()
                if line and not line.startswith("--"):
                    lines.append(line)

            cleaned_stmt = " ".join(lines).strip()
            if cleaned_stmt:
                statements.append(cleaned_stmt)

        return statements
