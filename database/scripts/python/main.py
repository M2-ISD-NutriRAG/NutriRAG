"""
Main entry point for NutriRAG data pipeline.

This script orchestrates the complete data pipeline:
1. Create Snowflake schema and tables from schema_db.sql
2. Load data from Google Drive and Kaggle
3. Clean and transform the data
4. Ingest into Snowflake

Usage:
    python main.py [options]
    
Options:
    --setup-only              Only setup Snowflake schema
    --load-only               Only load data
    --clean-only              Only clean data
    --ingest-only             Only ingest data
    --sql-inserts             Generate SQL inserts only
    --process-ingredients     Process ingredients only
    --nrows N                 Limit number of rows to process
"""

import argparse
import logging
import sys

from dotenv import load_dotenv

from PipelineOrchestrator import PipelineOrchestrator
from SnowflakeUtils import SnowflakeUtils

# Load environment variables from .env file
load_dotenv()


def setup_logging():
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


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
    parser.add_argument(
        "--sql-inserts",
        action="store_true",
        help="Generate SQL inserts only"
    )
    parser.add_argument(
        "--process-ingredients",
        action="store_true",
        help="Process and parse ingredients with unit conversion"
    )
    parser.add_argument(
        "--ingredients-sql",
        action="store_true",
        help="Process ingredients server-side in Snowflake (SQL/UDF)"
    )
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Limit number of rows to process"
    )

    args = parser.parse_args()
    logger = setup_logging()

    try:
        logger.info("🚀 Starting NutriRAG Data Pipeline")

        orchestrator = PipelineOrchestrator()

        # Process individual phases if requested
        if args.setup_only:
            connector = SnowflakeUtils()
            orchestrator.phase_0_setup_schema(connector)
            logger.info("🎉 SETUP COMPLETED SUCCESSFULLY!")
            return

        if args.ingest_only:
            connector = SnowflakeUtils()
            orchestrator.phase_3_ingest_data(connector)
            logger.info("🎉 DATA INGESTION COMPLETED SUCCESSFULLY!")
            return


        # Run full pipeline if no specific phase requested
        orchestrator.run_full_pipeline(nrows=args.nrows)

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
