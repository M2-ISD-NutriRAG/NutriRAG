import logging
import os
import pandas as pd
from snowflake.snowpark.functions import col

from config import SNOWFLAKE_CONFIG, SQL_DIR
from DataTransformer import DataTransformer
from SnowflakeUtils import SnowflakeUtils

class CleanData:
    """Orchestrates the ingestion process into Snowflake. Generates clean_recipes table"""

    def __init__(self, connector: SnowflakeUtils, transformer: DataTransformer):
        self.connector = connector
        self.transformer = transformer
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_ingestion_sql(self):
        """
        Server-side ingestion using SQL only.
        Much faster than loading everything to Pandas locally.
        """
        self.logger.info("=" * 60)
        self.logger.info("INGESTION: Server-side SQL processing")
        self.logger.info("=" * 60)

        try:
            # Load SQL template
            sql_path = os.path.join(SQL_DIR, "ingest_clean_recipes.sql")
            if not os.path.exists(sql_path):
                raise FileNotFoundError(f"Ingestion SQL not found: {sql_path}")
            
            self.logger.info(f"Loading SQL from: {sql_path}")
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_template = f.read()
            
            # Replace placeholders with actual config values
            sql = sql_template.format(
                database=SNOWFLAKE_CONFIG['database'],
                raw_schema=SNOWFLAKE_CONFIG['raw_schema'],
                cleaned_schema=SNOWFLAKE_CONFIG['cleaned_schema'],
                dev_schema=SNOWFLAKE_CONFIG['dev_schema'],
                raw_table=SNOWFLAKE_CONFIG['raw_table'],
                cleaned_table=SNOWFLAKE_CONFIG['cleaned_table'],
                recipes_enhanced_v2_table=SNOWFLAKE_CONFIG['recipes_enhanced_v2_table'],
                recipes_w_search_terms_table=SNOWFLAKE_CONFIG['recipes_w_search_terms_table']
            )
            
            # Split into statements and execute
            statements = []
            for stmt in sql.split(';'):
                # Remove comments and empty lines
                lines = []
                for line in stmt.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('--'):
                        lines.append(line)
                
                cleaned_stmt = ' '.join(lines).strip()
                if cleaned_stmt:
                    statements.append(cleaned_stmt)
            
            self.logger.info(f"Found {len(statements)} SQL statements to execute")
            
            for idx, stmt in enumerate(statements, 1):
                self.logger.info(f"Executing statement {idx}/{len(statements)}...")
                stmt_preview = stmt[:100].replace('\n', ' ')
                self.logger.debug(f"Statement: {stmt_preview}...")
                
                self.connector.safe_execute(stmt)
                self.logger.info(f"✅ Statement {idx} completed")
            
            self.logger.info("✅ Server-side ingestion completed successfully!")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise
     