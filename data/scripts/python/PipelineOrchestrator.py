"""
Pipeline Orchestrator for NutriRAG data processing.

Manages the complete data pipeline orchestration with clean separation of concerns.
Each phase is handled through dedicated methods that coordinate with existing classes.
"""

import logging
import os
import sys
from typing import Optional

import pandas as pd

from DataLoader import DataLoader
from DataTransformer import DataTransformer
from RecipeCleaner import RecipeCleaner
from SnowflakeConnector import SnowflakeConnector
from SnowFlakeIngestor import SnowflakeIngestor
from SqlInsertGenerator import SqlInsertGenerator
from IngredientParser import IngredientParser
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
        self.loader: Optional[DataLoader] = None
        self.connector: Optional[SnowflakeConnector] = None

    def phase_0_setup_schema(self) -> None:
        """
        PHASE 0: Create Snowflake schema and tables from schema_db.sql.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 0: SNOWFLAKE SCHEMA SETUP")
        self.logger.info("=" * 60)

        try:
            self.connector = SnowflakeConnector()

            # Get the path to schema_db.sql
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_file = os.path.join(script_dir, "..", "sql", "schema_db.sql")

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

                    self.connector.safe_execute(statement)
                    self.logger.info(f"✅ Statement {idx} executed")
                except Exception as e:
                    self.logger.error(f"❌ Error on statement {idx}: {e}")
                    self.logger.error(f"Statement: {statement[:200]}")
                    raise

            self.connector.close()
            self.logger.info("✅ Snowflake schema setup complete")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Schema setup failed: {e}", exc_info=True)
            raise

    def phase_1_load_data(self) -> DataLoader:
        """
        PHASE 1: Load data from local dataset folder.
        
        Returns:
            DataLoader instance with loaded data
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 1: DATA LOADING")
        self.logger.info("=" * 60)

        try:
            self.loader = DataLoader(cache_dir=CACHE_DIR)

            # Load from local dataset folder
            dataset_folder = "./dataset"
            self.logger.info(f"Loading data from local folder: {dataset_folder}")

            self.loader.load_from_local(dataset_folder, OUTPUT_FILES["raw_recipes"])
            self.loader.load_from_local(dataset_folder, OUTPUT_FILES["raw_interactions"])
            self.loader.load_from_local(dataset_folder, OUTPUT_FILES["cleaned_ingredients"])
            self.loader.load_from_local(
                os.path.join(dataset_folder, "data"),
                OUTPUT_FILES["recipes_w_search_terms"]
            )
            self.loader.load_from_local(dataset_folder, OUTPUT_FILES["recipes_images"])

            self.logger.info("✅ Data loading complete")
            self.logger.info("=" * 60)

            return self.loader

        except Exception as e:
            self.logger.error(f"Data loading failed: {e}", exc_info=True)
            raise

    def phase_1b_generate_raw_inserts(self, nrows: Optional[int] = None) -> None:
        """
        PHASE 1B: Generate SQL insert files for raw data CSVs.
        
        Args:
            nrows: Optional limit on number of rows to process
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 1B: GENERATE RAW SQL INSERTS")
        self.logger.info("=" * 60)

        try:
            generator = SqlInsertGenerator()

            raw_insert_specs = [
                ("raw_recipes", "raw_recipes_inserts.sql", 
                 f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['raw_table']}"),
                ("raw_interactions", "raw_interactions_inserts.sql",
                 f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.RAW_INTERACTION_10K"),
                ("cleaned_ingredients", "cleaned_ingredients_inserts.sql",
                 f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.CLEANED_INGREDIENTS"),
                ("recipes_images", "recipes_enhanced_v2_inserts.sql",
                 f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_enhanced_v2_table']}"),
                ("recipes_w_search_terms", "recipes_w_search_terms_inserts.sql",
                 f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_w_search_terms_table']}"),
            ]

            for file_key, sql_file, table_fqn in raw_insert_specs:
                sql_path = os.path.join(SQL_DIR, sql_file)
                if os.path.exists(sql_path):
                    self.logger.info(f"SQL inserts already exist: {sql_file}")
                    continue

                csv_path = os.path.join(CACHE_DIR, OUTPUT_FILES.get(file_key, ""))
                if not csv_path or not os.path.exists(csv_path):
                    self.logger.warning(f"CSV not found for {file_key}, skipping")
                    continue

                self.logger.info(f"Generating SQL inserts for {file_key}...")
                generator.generate_raw(csv_path, table_fqn, sql_path, nrows=nrows)
                self.logger.info(f"✅ {file_key} SQL generated: {sql_path}")

            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Generate raw inserts failed: {e}", exc_info=True)
            raise

    def phase_1c_load_raw_data(self,nrows) -> None:
        """
        PHASE 1C: Fast load raw data directly to Snowflake via write_pandas.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 1C: FAST LOAD RAW DATA (WRITE_PANDAS)")
        self.logger.info("=" * 60)

        connector = SnowflakeConnector()

        load_tasks = [
            ("ingredients_parsing", SNOWFLAKE_CONFIG['raw_schema'], SNOWFLAKE_CONFIG['ingredients_parsing_table']),
            ("raw_recipes", SNOWFLAKE_CONFIG['raw_schema'], SNOWFLAKE_CONFIG['raw_table']),
            ("raw_interactions", SNOWFLAKE_CONFIG['raw_schema'], "RAW_INTERACTION_10K"),
            ("cleaned_ingredients", SNOWFLAKE_CONFIG['raw_schema'], "CLEANED_INGREDIENTS"),
            ("recipes_images", SNOWFLAKE_CONFIG['raw_schema'], "RECIPES_ENHANCED_V2"),
            ("recipes_w_search_terms", SNOWFLAKE_CONFIG['raw_schema'], "RECIPES_W_SEARCH_TERMS"),
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
        finally:
            connector.close()

    def phase_2_clean_data(self) -> None:
        """
        PHASE 2: Clean and transform data.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 2: DATA CLEANING & TRANSFORMATION")
        self.logger.info("=" * 60)

        try:
            cleaned_csv_path = os.path.join(CACHE_DIR, OUTPUT_FILES["cleaned_recipes"])
            if os.path.exists(cleaned_csv_path):
                self.logger.info(f"Cleaned recipes file already exists: {cleaned_csv_path}")
                self.logger.info("Skipping cleaning phase (already processed)")
                return

            if self.loader is None:
                self.loader = DataLoader(cache_dir=CACHE_DIR)

            cleaner = RecipeCleaner(self.loader)
            cleaner.run_transformation(consistency_check=False)

            self.logger.info("✅ Data cleaning complete")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Data cleaning failed: {e}", exc_info=True)
            raise

    def phase_2b_generate_sql_inserts(self, nrows: Optional[int] = None) -> None:
        """
        PHASE 2B: Generate SQL insert file from cleaned recipes CSV.
        
        Args:
            nrows: Optional limit on number of rows to process
        """
        sql_inserts = os.path.join(SQL_DIR, OUTPUT_FILES["db_inserts"])
        if os.path.exists(sql_inserts):
            self.logger.info(f"SQL inserts file already exists: {sql_inserts}")
            return

        self.logger.info("=" * 60)
        self.logger.info("PHASE 2B: GENERATE SQL INSERTS")
        self.logger.info("=" * 60)

        try:
            generator = SqlInsertGenerator()
            sql_path = generator.generate(nrows=nrows)
            self.logger.info(f"✅ SQL insert file generated: {sql_path}")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Generate SQL inserts failed: {e}", exc_info=True)
            raise

    def phase_3_ingest_data(self) -> None:
        """
        PHASE 3: Ingest data into Snowflake.
        """
        self.logger.info("=" * 60)
        self.logger.info("PHASE 3: SNOWFLAKE INGESTION")
        self.logger.info("=" * 60)

        try:
            connector = SnowflakeConnector()
            transformer = DataTransformer()
            ingestor = SnowflakeIngestor(connector, transformer)

            ingestor.run_ingestion()

            connector.close()
            self.logger.info("✅ Data ingestion complete")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise

    def process_ingredients(self) -> pd.DataFrame:
        """
        Process ingredients with unit conversion and parsing.
        
        Returns:
            Processed DataFrame
        """
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING INGREDIENTS")
        self.logger.info("=" * 60)

        try:
            parser = IngredientParser()
            df_final = parser.main()
            self.logger.info(f"✅ Ingredients processed successfully")
            self.logger.info(f"   Output: ./dataset/ingredients_exploded.csv")
            self.logger.info(f"   Total records: {len(df_final)}")
            return df_final
        except Exception as e:
            self.logger.error(f"Ingredient processing failed: {e}", exc_info=True)
            raise

    def run_full_pipeline(self, nrows: Optional[int] = None) -> None:
        """
        Run the complete data pipeline.
        
        Args:
            nrows: Optional limit on number of rows to process
        """
        try:
            self.process_ingredients()
            self.phase_0_setup_schema() # create snowflake schema
            # self.phase_1_load_data() # load csv files
            # self.phase_1b_generate_raw_inserts(nrows)
            self.phase_1c_load_raw_data(nrows) # fast load to snowflake
            # self.phase_2_clean_data() 
            # self.phase_2b_generate_sql_inserts(nrows)
            self.phase_3_ingest_data() # generate clean data to save to snowflake
            self.logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            raise

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
