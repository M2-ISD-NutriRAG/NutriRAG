"""Search Service Module.

Provides hybrid search capabilities combining vector semantic search and BM25
lexical search. Supports flexible filtering, result ranking via Reciprocal Rank
Fusion (RRF), and integration with Snowflake procedures.
"""

import json
import os
from typing import Any, Dict, List, Optional

from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc

from app.models.search import SearchFilters
from app.services.bm25_service import BM25Service
from app.services.vector_search_service import VectorSearchService
from app.utils.filter_builder import (
    build_filter_conditions as build_filters_util,
)
from shared.snowflake.client import SnowflakeClient


class SearchResponseException(Exception):
    """Exception raised when search operation fails.

    Includes contextual information about the failed search including query,
    execution time, and error message.

    Attributes:
        query: The search query that failed.
        execution_time_ms: Execution time in milliseconds.
        error_message: Description of the error.
    """

    def __init__(
        self,
        query: str,
        execution_time_ms: float,
        error_message: str,
    ):
        self.query = query
        self.execution_time_ms = execution_time_ms
        self.error_message = error_message
        super().__init__(error_message)


class SearchService:
    """Hybrid search service combining vector and BM25 algorithms.

    Provides a unified interface for semantic search using embeddings and
    lexical search using BM25. Supports flexible filtering, result ranking
    via Reciprocal Rank Fusion (RRF), and agent tool integration.

    Attributes:
        client: Snowflake client for database operations.
        stage_name: Snowflake stage location for storing search utilities.
    """

    def __init__(
        self,
        snowflake_client: Optional[SnowflakeClient] = None,
        setup: bool = False,
    ):
        """Initialize the Search Service.

        Args:
            snowflake_client: Optional Snowflake client instance. If None,
                creates a new SnowflakeClient.
            setup: If True, initializes BM25 and vector search services,
                creates stages, uploads utilities, and registers procedures.
        """
        self.client = snowflake_client or SnowflakeClient()
        self.stage_name = "@VECTORS.search_stage"

        if setup:
            try:
                bm25_service = BM25Service(self.client, setup=True)
                bm25_service.build_index(
                    source_table="ENRICHED.RECIPES_SAMPLE_50K",
                    text_columns=[
                        "NAME",
                        "DESCRIPTION",
                        "TAGS",
                        "INGREDIENTS",
                        "SEARCH_TERMS",
                        "FILTERS",
                    ],
                    id_column="ID",
                    field_weights={
                        "NAME": 3,
                        "DESCRIPTION": 2,
                        "TAGS": 2,
                        "INGREDIENTS": 1,
                        "SEARCH_TERMS": 2,
                        "FILTERS": 1,
                    },
                )
            except Exception as e:
                print(f"Warning: Failed to setup BM25Service: {str(e)}")

            try:
                _ = VectorSearchService(self.client, setup=True)
            except Exception as e:
                print(f"Warning: Failed to setup VectorSearchService: {str(e)}")

            self._setup_stage()
            self._upload_utils_to_stage()
            self._setup_combined_search_procedure()
            self._setup_search_tool_procedure()

    def _setup_stage(self) -> None:
        """Create Snowflake stage for storing search utilities."""
        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS VECTORS.search_stage
            DIRECTORY = (ENABLE = TRUE)
            COMMENT = 'Stage for storing search utility files'
        """
        try:
            self.client.execute(create_stage_sql)
        except Exception as e:
            raise RuntimeError(f"Failed to create search stage: {str(e)}")

    def _upload_utils_to_stage(self) -> None:
        """Upload utility files and models to Snowflake stage."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(current_dir, "..", "utils")
        models_dir = os.path.join(current_dir, "..", "models")

        # Files to upload from utils directory
        utils_files = ["search_combine_utils.py", "filter_builder.py"]

        # Files to upload from models directory
        model_files = ["search.py", "recipe.py"]

        # Upload utility files
        for util_file in utils_files:
            util_path = os.path.join(utils_dir, util_file)

            if not os.path.exists(util_path):
                raise FileNotFoundError(f"{util_file} not found at {util_path}")

            # Convert to UNIX-style path for Snowflake
            abs_path = os.path.abspath(util_path).replace("\\", "/")

            put_sql = f"""
            PUT 'file://{abs_path}'
            {self.stage_name}
            AUTO_COMPRESS = FALSE
            OVERWRITE = TRUE
            """

            try:
                self.client.execute(put_sql)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to upload {util_file} to stage: {str(e)}"
                )

        # Upload model files
        for model_file in model_files:
            model_path = os.path.join(models_dir, model_file)

            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"{model_file} not found at {model_path}"
                )

            # Convert to UNIX-style path for Snowflake
            abs_path = os.path.abspath(model_path).replace("\\", "/")

            put_sql = f"""
            PUT 'file://{abs_path}'
            {self.stage_name}
            AUTO_COMPRESS = FALSE
            OVERWRITE = TRUE
            """

            try:
                self.client.execute(put_sql)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to upload {model_file} to stage: {str(e)}"
                )

    def _setup_combined_search_procedure(self) -> None:
        """Register the SEARCH_SIMILAR_RECIPES stored procedure."""
        session = self.client.get_snowpark_session()

        @sproc(
            session=session,
            name="VECTORS.SEARCH_SIMILAR_RECIPES",
            packages=["snowflake-snowpark-python", "pydantic"],
            is_permanent=True,
            stage_location="@VECTORS.search_stage",
            imports=[
                "@VECTORS.search_stage/search.py",
                "@VECTORS.search_stage/search_combine_utils.py",
                "@VECTORS.search_stage/filter_builder.py",
                "@VECTORS.search_stage/recipe.py",
            ],
            replace=True,
            python_version="3.10",
        )
        def search_similar_recipes(
            session: Session,
            query_text: str,
            top_k: int,
            filters: Optional[str] = None,
            vector_weight: float = 0.7,
            bm25_weight: float = 0.3,
            index_table: str = "VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table: str = "ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table: str = "VECTORS.RECIPES_50K_EMBEDDINGS",
        ) -> list:
            """Search recipes combining vector and BM25 results."""
            import json
            import search_combine_utils
            import filter_builder

            try:
                # Build filter conditions from filters JSON
                filter_conditions = None
                if filters and filters != "NULL":
                    filters_dict = json.loads(filters)
                    filter_conditions = filter_builder.build_filter_conditions(
                        filters_dict
                    )

                # Execute vector search with filters
                fetch_size = max(top_k * 5, 60)  # Fetch more for better merging
                if filter_conditions:
                    safe_conditions = filter_conditions.replace("'", "''")
                    filter_param = f"'{safe_conditions}'"
                else:
                    filter_param = "NULL"
                query_escaped = query_text.replace("'", "''")
                vector_sql = f"CALL VECTORS.SEARCH_SEMANTIC('{query_escaped}', '{embeddings_table}', {fetch_size}, {filter_param})"
                try:
                    vector_results = json.loads(
                        session.sql(vector_sql).collect()[0][0]
                    )
                except (json.JSONDecodeError, IndexError, TypeError):
                    vector_results = []

                # Execute BM25 search with filters
                bm25_sql = f"CALL VECTORS.SEARCH_BM25('{query_escaped}', '{index_table}', '{source_table}', {fetch_size}, {filter_param})"
                try:
                    bm25_results = json.loads(
                        session.sql(bm25_sql).collect()[0][0]
                    )
                except (json.JSONDecodeError, IndexError, TypeError):
                    bm25_results = []

                # Combine and rank results using utility function
                final_results = search_combine_utils.combine_results(
                    vector_results=vector_results,
                    bm25_results=bm25_results,
                    top_k=top_k,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight,
                    boost_consensus=1.15,
                )

                return final_results

            except Exception as e:
                import traceback

                error_info = {
                    "error": str(e),
                    "type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                }
                return [error_info]

    def _setup_search_tool_procedure(self) -> None:
        """Register the SEARCH_SIMILAR_RECIPES_TOOL agent procedure."""
        create_tool_proc_sql = """
        CREATE OR REPLACE PROCEDURE SERVICES.SEARCH_SIMILAR_RECIPES_TOOL(
            user_input STRING,
            query_input STRING,
            k_input INT,
            filters_input VARCHAR DEFAULT NULL
        )
        RETURNS OBJECT
        LANGUAGE PYTHON
        RUNTIME_VERSION = '3.10'
        PACKAGES = ('snowflake-snowpark-python', 'pydantic')
        IMPORTS = ('@VECTORS.search_stage/search.py', '@VECTORS.search_stage/search_combine_utils.py', '@VECTORS.search_stage/filter_builder.py', '@VECTORS.search_stage/recipe.py')
        HANDLER = 'search_tool_handler'
        AS
        $$
def search_tool_handler(session, user_input, query_input, k_input, filters_input):
    import json
    from datetime import datetime
    import time
    from search import SearchRequest, SearchResponse

    try:
        start_time = time.time()

        # 1. Parse and validate filters if provided
        filters_dict = None
        if filters_input and filters_input != "NULL":
            try:
                filters_dict = json.loads(filters_input)
            except json.JSONDecodeError:
                raise ValueError("filters must be valid JSON")

        # 2. Validate input against SearchRequest model
        search_request = SearchRequest(
            user=user_input,
            query=query_input,
            k=k_input,
            filters=filters_dict
        )

        # 3. Call the main search procedure
        if filters_dict:
            filters_param = "PARSE_JSON('" + json.dumps(filters_dict).replace("'", "''") + "')"
        else:
            filters_param = "NULL"

        query_escaped = search_request.query.replace("'", "''")
        call_sql = f"\"\"
        CALL VECTORS.SEARCH_SIMILAR_RECIPES(
            '{query_escaped}',
            {search_request.k},
            {filters_param},
            0.7,
            0.3,
            'VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX',
            'ENRICHED.RECIPES_SAMPLE_50K',
            'VECTORS.RECIPES_50K_EMBEDDINGS'
        )
        "\"\"

        results_raw = session.sql(call_sql).collect()

        # Parse search results
        if results_raw:
            results_json = json.loads(results_raw[0][0])
        else:
            results_json = []

        # Build and validate response
        execution_time_ms = (time.time() - start_time) * 1000

        response = SearchResponse(
            results=results_json if isinstance(results_json, list) else [],
            query=search_request.query,
            total_found=len(results_json) if isinstance(results_json, list) else 0,
            execution_time_ms=execution_time_ms,
            status="success"
        )

        return response.model_dump_json()

    except Exception as e:
        import traceback
        execution_time_ms = (time.time() - start_time) * 1000

        # Return error response (note: SearchResponse may not have error field, so we return JSON directly)
        error_response = {
            "results": [],
            "query": query_input,
            "total_found": 0,
            "execution_time_ms": execution_time_ms,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

        return error_response
$$
        """
        try:
            self.client.execute(create_tool_proc_sql)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create SEARCH_SIMILAR_RECIPES_TOOL procedure: {str(e)}"
            )

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        index_table: str = "VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
        source_table: str = "ENRICHED.RECIPES_SAMPLE_50K",
        embeddings_table: str = "VECTORS.RECIPES_50K_EMBEDDINGS",
    ) -> List[Dict[str, Any]]:
        """Execute hybrid search combining vector and BM25 results.

        Performs semantic search using embeddings and lexical search using BM25,
        then merges and ranks results via Reciprocal Rank Fusion.

        Args:
            query: Search query text.
            filters: Optional filter dict or SearchFilters object with numeric_filters,
                dietary_filters, include_ingredients, exclude_ingredients,
                and any_ingredients.
            limit: Maximum number of results to return. Defaults to 10.
            vector_weight: Weight for vector search scores. Defaults to 0.7.
            bm25_weight: Weight for BM25 search scores. Defaults to 0.3.
            index_table: BM25 index table name. Defaults to
                "VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX".
            source_table: Source table for recipe data. Defaults to
                "ENRICHED.RECIPES_SAMPLE_50K".
            embeddings_table: Embeddings table name. Defaults to
                "VECTORS.RECIPES_50K_EMBEDDINGS".

        Returns:
            List of search results ranked by combined hybrid score.
        """
        # Convert SearchFilters object to dict if needed
        filters_dict = None
        if filters:
            if isinstance(filters, SearchFilters):
                # Convert SearchFilters object to dictionary
                filters_dict = {
                    "numeric_filters": (
                        [
                            {
                                "name": nf.name,
                                "operator": nf.operator,
                                "value": nf.value,
                            }
                            for nf in filters.numeric_filters
                        ]
                        if filters.numeric_filters
                        else []
                    ),
                    "dietary_filters": filters.dietary_filters or [],
                    "include_ingredients": filters.include_ingredients or [],
                    "exclude_ingredients": filters.exclude_ingredients or [],
                    "any_ingredients": filters.any_ingredients or [],
                }
            else:
                filters_dict = filters

            build_filters_util(filters_dict)  # Validation happens here

        filters_json_str = json.dumps(filters_dict) if filters_dict else "NULL"

        sql = f"""
        CALL VECTORS.SEARCH_SIMILAR_RECIPES(
            '{query.replace("'", "''")}',
            {limit},
            PARSE_JSON('{filters_json_str}'),
            {vector_weight},
            {bm25_weight},
            '{index_table}',
            '{source_table}',
            '{embeddings_table}'
        )
        """

        try:
            results = self.client.execute(sql, fetch="all")
            if not results:
                return []

            return json.loads(results[0][0])
        except (json.JSONDecodeError, IndexError, TypeError):
            return []
