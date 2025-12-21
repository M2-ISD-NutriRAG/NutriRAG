"""
Main entry point for NutriRAG data pipeline.

This script orchestrates the complete data pipeline:
1. Create Snowflake schema and tables from schema_db.sql
2. Load data from Google Drive and Kaggle
3. Clean and transform the data
4. Ingest into Snowflake

Usage:
    export SNOWFLAKE_ACCOUNT=<account>
    export SNOWFLAKE_USER=<user>
    export SNOWFLAKE_PRIVATE_KEY_PATH=<path>
    export SNOWFLAKE_ROLE=<role>
    python main.py [--setup-only] [--load-only] [--clean-only] [--ingest-only]
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from DataLoader import DataLoader
from DataTransformer import DataTransformer
from RecipeCleaner import RecipeCleaner
from SnowflakeConnector import SnowflakeConnector
from SnowFlakeIngestor import SnowflakeIngestor
from SqlInsertGenerator import SqlInsertGenerator
from config import (
    GOOGLE_DRIVE_FILES,
    KAGGLE_DATASETS,
    OUTPUT_FILES,
    SNOWFLAKE_CONFIG,
    DATA_PARAMS,
    CACHE_DIR,
    SQL_DIR
)

# Load environment variables from .env file
load_dotenv()


def setup_logging():
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def setup_snowflake_schema(logger):
    """Create Snowflake database and tables from schema_db.sql."""
    logger.info("=" * 60)
    logger.info("PHASE 0: SNOWFLAKE SCHEMA SETUP")
    logger.info("=" * 60)

    try:
        connector = SnowflakeConnector()
        
        # Get the path to schema_db.sql
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_file = os.path.join(script_dir, "..", "sql", "schema_db.sql")
        
        if not os.path.exists(schema_file):
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        logger.info(f"Reading schema from: {schema_file}")
        
        # Read and execute SQL file
        with open(schema_file, "r") as f:
            sql_content = f.read()
        
        # Split by semicolon and clean statements
        statements = []
        for stmt in sql_content.split(";"):
            # Remove leading/trailing whitespace
            stmt = stmt.strip()
            
            # Remove comment-only lines
            lines = []
            for line in stmt.split("\n"):
                line = line.strip()
                # Skip empty lines and comment-only lines
                if line and not line.startswith("--"):
                    lines.append(line)
            
            # Reconstruct statement
            cleaned_stmt = " ".join(lines).strip()
            if cleaned_stmt:
                statements.append(cleaned_stmt)
        
        logger.info(f"Found {len(statements)} SQL statements (after filtering comments)")
        
        for idx, statement in enumerate(statements, 1):
            try:
                logger.info(f"Executing statement {idx}/{len(statements)}...")
                # Log first 80 chars of statement
                stmt_preview = statement[:80].replace("\n", " ")
                logger.debug(f"Statement: {stmt_preview}...")
                
                connector.safe_execute(statement)
                logger.info(f"✅ Statement {idx} executed")
            except Exception as e:
                logger.error(f"❌ Error on statement {idx}: {e}")
                logger.error(f"Statement: {statement[:200]}")
                raise
        
        connector.close()
        logger.info("✅ Snowflake schema setup complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Schema setup failed: {e}", exc_info=True)
        raise


def load_data(logger):
    """Load data from local dataset folder."""
    logger.info("=" * 60)
    logger.info("PHASE 1: DATA LOADING")
    logger.info("=" * 60)

    loader = DataLoader(cache_dir=CACHE_DIR)

    # Load from local dataset folder
    dataset_folder = "data/scripts/python/"  # Adjust this path as needed
    logger.info(f"Loading data from local folder: {dataset_folder}")

    raw_recipes_path = loader.load_from_local(
        dataset_folder,
        OUTPUT_FILES["raw_recipes"]
    )
    raw_interactions_path = loader.load_from_local(
        dataset_folder,
        OUTPUT_FILES["raw_interactions"]
    )
    cleaned_ingredients_path = loader.load_from_local(
        dataset_folder,
        OUTPUT_FILES["cleaned_ingredients"]
    )

    # For recipes_w_search_terms, it's in a subfolder
    recipes_w_search_terms_path = loader.load_from_local(
        os.path.join(dataset_folder, "data"),
        OUTPUT_FILES["recipes_w_search_terms"]
    )

    # For recipes_images, assume it's in the same folder or skip if not needed
    recipes_images_path = loader.load_from_local(
        dataset_folder,
        OUTPUT_FILES["recipes_images"]
    )

    logger.info("✅ Data loading complete")
    logger.info("=" * 60)

    return loader


def clean_data(logger, loader):
    """Clean and transform data."""
    logger.info("=" * 60)
    logger.info("PHASE 2: DATA CLEANING & TRANSFORMATION")
    logger.info("=" * 60)

    # Check if cleaned recipes file already exists
    cleaned_csv_path = os.path.join(CACHE_DIR, OUTPUT_FILES["cleaned_recipes"])
    if os.path.exists(cleaned_csv_path):
        logger.info(f"Cleaned recipes file already exists: {cleaned_csv_path}")
        logger.info("Skipping cleaning phase (already processed)")
        return

    cleaner = RecipeCleaner(loader)
    cleaner.run_transformation(consistency_check=False)

    logger.info("✅ Data cleaning complete")
    logger.info("=" * 60)


def ingest_data(logger):
    """Ingest data into Snowflake."""
    logger.info("=" * 60)
    logger.info("PHASE 3: SNOWFLAKE INGESTION")
    logger.info("=" * 60)

    try:
        connector = SnowflakeConnector()
        transformer = DataTransformer()
        ingestor = SnowflakeIngestor(connector, transformer)
        
        ingestor.run_ingestion()
        
        connector.close()
        logger.info("✅ Data ingestion complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise


def generate_sql_inserts(logger):
    """Generate SQL insert file from cleaned recipes CSV."""

    sql_inserts = os.path.join(SQL_DIR, OUTPUT_FILES["db_inserts"])
    if os.path.exists(sql_inserts):
        logger.info(f"SQL inserts file already exists: {sql_inserts}")
        logger.info("Skipping generation (already processed)")
        return

    logger.info("=" * 60)
    logger.info("PHASE 2B: GENERATE SQL INSERTS")
    logger.info("=" * 60)

    generator = SqlInsertGenerator()
    sql_path = generator.generate()
    logger.info(f"✅ SQL insert file generated: {sql_path}")
    logger.info("=" * 60)


def execute_sql_inserts(logger):
    """Execute the SQL insert file in Snowflake."""
    logger.info("=" * 60)
    logger.info("PHASE 2C: EXECUTE SQL INSERTS")
    logger.info("=" * 60)

    sql_inserts_path = os.path.join(SQL_DIR, OUTPUT_FILES["db_inserts"])
    
    if not os.path.exists(sql_inserts_path):
        raise FileNotFoundError(f"SQL inserts file not found: {sql_inserts_path}")
    
    logger.info(f"Reading SQL inserts from: {sql_inserts_path}")
    
    try:
        connector = SnowflakeConnector()

        # Ensure warehouse/database/schema are active for this session
        wh = os.environ.get("SNOWFLAKE_WAREHOUSE")
        db = os.environ.get("SNOWFLAKE_DATABASE") or SNOWFLAKE_CONFIG.get("database")
        sch = os.environ.get("SNOWFLAKE_SCHEMA") or SNOWFLAKE_CONFIG.get("cleaned_schema")

        if wh:
            logger.info(f"Using warehouse: {wh}")
            connector.safe_execute(f"USE WAREHOUSE {wh}")
        if db:
            logger.info(f"Using database: {db}")
            connector.safe_execute(f"USE DATABASE {db}")
        if sch:
            logger.info(f"Using schema: {sch}")
            connector.safe_execute(f"USE SCHEMA {sch}")
        
        with open(sql_inserts_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        logger.info(f"Found {len(statements)} INSERT statements to execute")
        
        for idx, statement in enumerate(statements, 1):
            try:
                if idx % 1000 == 0:
                    logger.info(f"Executing statement {idx}/{len(statements)}...")
                
                connector.safe_execute(statement)
            except Exception as e:
                logger.error(f"❌ Error on statement {idx}: {e}")
                logger.error(f"Statement: {statement[:200]}")
                raise
        
        connector.close()
        logger.info(f"✅ Successfully executed {len(statements)} INSERT statements")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"SQL inserts execution failed: {e}", exc_info=True)
        raise


def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="NutriRAG Data Pipeline"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only setup Snowflake schema, skip other phases"
    )
    parser.add_argument(
        "--load-only",
        action="store_true",
        help="Only load data, skip setup and other phases"
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean data, skip setup and loading"
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Only ingest data, skip all other phases"
    )

    args = parser.parse_args()
    logger = setup_logging()

    try:
        logger.info("🚀 Starting NutriRAG Data Pipeline")

        loader = None

        # Phase 0: Setup Snowflake schema
        if not args.load_only and not args.clean_only and not args.ingest_only:
            setup_snowflake_schema(logger)
        elif args.setup_only:
            setup_snowflake_schema(logger)
            logger.info("🎉 SETUP COMPLETED SUCCESSFULLY!")
            return

        # Phase 1: Load
        if not args.clean_only and not args.ingest_only:
            loader = load_data(logger)
        elif args.load_only:
            loader = load_data(logger)
            logger.info("🎉 DATA LOADING COMPLETED SUCCESSFULLY!")
            return

        # Phase 2: Clean
        if not args.ingest_only:
            if loader is None:
                loader = DataLoader(cache_dir=CACHE_DIR)
            clean_data(logger, loader)
            generate_sql_inserts(logger)
        elif args.clean_only:
            if loader is None:
                loader = DataLoader(cache_dir=CACHE_DIR)
            clean_data(logger, loader)
            generate_sql_inserts(logger)
            logger.info("🎉 DATA CLEANING COMPLETED SUCCESSFULLY!")
            return

        # Phase 2C: Execute SQL inserts
        if not args.load_only and not args.clean_only:
            execute_sql_inserts(logger)
        elif args.ingest_only:
            execute_sql_inserts(logger)

        # Phase 3: Ingest
        if not args.load_only and not args.clean_only:
            ingest_data(logger)
        elif args.ingest_only:
            ingest_data(logger)
            logger.info("🎉 DATA INGESTION COMPLETED SUCCESSFULLY!")
            return

        logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()