"""Create Vector Database Service.

Provides functionality to create vector databases for semantic search."""

import json
import os
import time
import pandas as pd
from typing import Any, Dict, List, Optional

from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc

from shared.snowflake.client import SnowflakeClient


class CreateVectorDatabaseService:
    """Service to create vector databases.

    Attributes:
        client (SnowflakeClient): Client to interact with Snowflake database.
    """

    def __init__(
        self,
        snowflake_client: Optional[SnowflakeClient] = None,
        stage_name: str = "VECTORS.create_vector_db_notebook_stage",
        notebook_name: str = "create_vector_db",
        setup: bool = False,
        source_table: str = "",
        output_table: str = "",
        id_column: str = "",
        columns_to_embedd: List[str] = [],
        embedding_model: str = "",
    ):
        """Initialise the Create Vector Database Service

        Args:
            snowflake_client (Optional[SnowflakeClient]): An optional Snowflake client instance.
            embedding_model (Optional[str]): The embedding model to use.
            setup (bool): Whether to perform setup operations.
        """
        self.client = snowflake_client or SnowflakeClient()
        self.stage_name = stage_name
        self.notebook_name = notebook_name
        self.source_table = source_table
        self.output_table = output_table
        self.id_column = id_column
        self.columns_to_embedd = columns_to_embedd
        self.embedding_model = embedding_model

        if setup:
            self._setup_stage()

    def _setup_stage(self) -> None:
        """Create Snowflake stage for storing nootbook to create the vector database."""

        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS {self.stage_name}
            DIRECTORY = (ENABLE = TRUE)
            COMMENT = 'Stage for storing function to clean columns for vector database embedding'
        """

        try:
            self.client.execute(create_stage_sql)
        except Exception as e:
            pass

        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_path = os.path.join(current_dir, f"../utils/{self.notebook_name}.ipynb")

        if not os.path.isfile(utils_path):
            raise FileNotFoundError(f"Utility file not found at path: {utils_path}")

        try:
            if not os.path.isfile(utils_path):
                raise FileNotFoundError(f"Utility file not found at path: {utils_path}")

            abs_path = os.path.abspath(utils_path).replace("\\", "/")

            put_sql = f"""
                PUT file://{abs_path} 
                @{self.stage_name}
                AUTO_COMPRESS=FALSE
                OVERWRITE=TRUE
                """
            self.client.execute(put_sql)
        except Exception as e:
            raise RuntimeError(
                f"Failed to upload utility files to Snowflake stage {str(e)}"
            )

    def create_vector_database(self) -> None:
        """Create the notebook then call it to create the vector database."""

        sql_create_notebook = f"""CREATE OR REPLACE NOTEBOOk {self.notebook_name}
            FROM @{self.stage_name}
            MAIN_FILE = '{self.notebook_name}.ipynb'
            QUERY_WAREHOUSE = 'NUTRIRAG_PROJECT'
            RUNTIME_NAME = 'SYSTEM$GPU_RUNTIME' 
            COMPUTE_POOL = 'SYSTEM_COMPUTE_POOL_GPU'
            EXTERNAL_ACCESS_INTEGRATIONS = ('training_internet_access');"""

        sql_activate_notebook = f"""ALTER NOTEBOOK {self.notebook_name} 
            ADD LIVE VERSION FROM LAST;"""

        sql_execute_notebook = f"""EXECUTE NOTEBOOK {self.notebook_name}(
            '{self.source_table}',
            '{self.output_table}', 
            '{self.id_column}',                                      
            '{",".join(self.columns_to_embedd)}',
            '{self.embedding_model}'
        ); """

        try:
            # Create the notebook
            self.client.execute(sql_create_notebook)

            # Verify notebook exists
            check_notebook = f"""
            SELECT COUNT(*) as cnt 
            FROM INFORMATION_SCHEMA.NOTEBOOKS 
            WHERE NOTEBOOK_NAME = '{self.notebook_name.upper()}'
            """
            result = self.client.execute(check_notebook, fetch="one")
            if result and result[0] > 0:
                print(f"✓ Notebook '{self.notebook_name}' created successfully")
            else:
                raise RuntimeError(f"Notebook '{self.notebook_name}' was not created")

            # Activate the notebook
            self.client.execute(sql_activate_notebook)

            # Execute the notebook
            self.client.execute(sql_execute_notebook)

            # check if output table was created
            check_output_table = f"""
            SELECT COUNT(*) as cnt
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{self.output_table.split('.')[-1]}'
            AND TABLE_SCHEMA = '{self.output_table.split('.')[0] if '.' in self.output_table else 'VECTORS'}'
            """
            result = self.client.execute(check_output_table, fetch="one")
            if result and result[0] > 0:
                # Check row count in output table
                check_rows = f"SELECT COUNT(*) as cnt FROM {self.output_table}"
                row_result = self.client.execute(check_rows, fetch="one")
                row_count = row_result[0] if row_result else 0
                print(
                    f"Output table '{self.output_table}' created with {row_count} rows"
                )
            else:
                print(
                    "warning: Output table not found (execution may still be running)"
                )

            print(f"\n✓ All steps completed successfully!")
        except Exception as e:
            raise RuntimeError(f"Failed to create notebook: {str(e)}")
