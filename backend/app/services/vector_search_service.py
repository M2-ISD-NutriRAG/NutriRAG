"""Vector Search Service Module.

Provides semantic similarity search capabilities using embeddings and cosine
similarity on Snowflake. Supports multiple embedding models including Snowflake
CORTEX models and custom Sentence Transformers.
"""

import json
import time
from typing import Any, Dict, List, Optional

from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc

from data.embeddings.config import EMBEDDING_MODEL as DEFAULT_EMBEDDING_MODEL
from shared.models.embedding_models import (
    EmbeddingModel,
    get_embedding_config
)
from shared.snowflake.client import SnowflakeClient


class VectorSearchService:
    """Semantic search service using embeddings and cosine similarity.

    Manages text embedding generation, model caching, and semantic search
    with support for multiple embedding models including Snowflake CORTEX
    and custom Sentence Transformer models.

    Attributes:
        client: Snowflake client for database operations.
        embedding_model: Selected embedding model identifier.
        model: Embedding model instance for query encoding.
        embedding_config: Configuration for the selected embedding model.
        stage_name: Snowflake stage location for storing models.
    """

    def __init__(
        self,
        snowflake_client: Optional[SnowflakeClient] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        setup: bool = False,
    ):
        """Initialize the Vector Search Service.

        Args:
            snowflake_client: Optional Snowflake client instance. If None,
                creates a new SnowflakeClient.
            embedding_model: Optional embedding model to use for query encoding.
                If None, uses the default model from config.
            setup: If True, creates stages and registers stored procedures.
        """
        self.client = snowflake_client or SnowflakeClient()
        # Use provided model or default from config (must match embeddings creation)
        self.embedding_model = embedding_model or DEFAULT_EMBEDDING_MODEL
        self.embedding_config = get_embedding_config(self.embedding_model)
        self.stage_name = "@VECTORS.embedding_models_stage"

        if setup:
            self._setup_stage()
            self._setup_embedding_procedure()
            self._setup_search_procedure()

    def _setup_stage(self) -> None:
        """Create Snowflake stage for storing embedding models."""
        create_stage_sql = f"""
        CREATE STAGE IF NOT EXISTS VECTORS.embedding_models_stage
            DIRECTORY = (ENABLE = TRUE)
            COMMENT = 'Stage for storing custom embedding models'
        """
        try:
            self.client.execute(create_stage_sql)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create embedding models stage: {str(e)}"
            )

    def _setup_embedding_procedure(self) -> None:
        """Register the embed_text_proc stored procedure."""
        session = self.client.get_snowpark_session()

        @sproc(
            session=session,
            name="VECTORS.embed_text_proc",
            packages=["snowflake-snowpark-python", "sentence-transformers"],
            is_permanent=True,
            stage_location="@VECTORS.embedding_models_stage",
            replace=True,
            external_access_integrations=["training_internet_access"],
            python_version="3.10",
        )
        def embed_text_proc(
            session: Session,
            text_input: str,
            model_name: str,
        ) -> str:
            """Generate embeddings for text using specified model."""
            import os
            import time
            import zipfile
            import json
            from sentence_transformers import SentenceTransformer

            os.environ["HF_HOME"] = "/tmp/huggingface"
            STAGE_NAME = "@VECTORS.embedding_models_stage"

            try:
                start_time = time.time()
                model_source = "UNKNOWN"

                SNOWFLAKE_MODELS = [
                    "e5-base-v2",
                    "multilingual-e5-large",
                    "snowflake-arctic-embed-m",
                    "snowflake-arctic-embed-l",
                ]

                if model_name in SNOWFLAKE_MODELS:
                    escaped_text = text_input.replace("'", "''")
                    size = (
                        "1024"
                        if model_name
                        in ["snowflake-arctic-embed-l", "multilingual-e5-large"]
                        else "768"
                    )
                    sql = (
                        "SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_"
                        + size
                        + "('"
                        + model_name
                        + "', '"
                        + escaped_text
                        + "') as embedding"
                    )

                    model_source = "CORTEX"
                    execution_time = time.time() - start_time
                    result = session.sql(sql).collect()
                    embedding = result[0]["EMBEDDING"]

                    return json.dumps(
                        {
                            "embedding": embedding,
                            "model_source": model_source,
                            "execution_time": execution_time,
                        }
                    )

                # Custom models with ZIP support
                normalized_model_name = model_name.replace("/", "_").replace(
                    "-", "_"
                )
                local_model_path = f"/tmp/{normalized_model_name}"
                zip_filename = f"{normalized_model_name}.zip"
                local_zip_path = f"/tmp/{zip_filename}"

                if os.path.exists(local_model_path):
                    model_source = "LOCAL_CACHE"
                else:
                    try:
                        # Check if ZIP exists in stage
                        stage_check = session.sql(
                            f"LIST {STAGE_NAME}/{zip_filename}"
                        ).collect()

                        if len(stage_check) > 0:
                            model_source = "STAGE"
                            # Download ZIP
                            session.file.get(
                                f"{STAGE_NAME}/{zip_filename}", "/tmp/"
                            )

                            # Extract
                            with zipfile.ZipFile(
                                local_zip_path, "r"
                            ) as zip_ref:
                                zip_ref.extractall(local_model_path)

                            # Clean up ZIP
                            os.remove(local_zip_path)
                        else:
                            model_source = "INTERNET_DOWNLOAD"
                            # Download model
                            model = SentenceTransformer(
                                model_name, cache_folder="/tmp/huggingface"
                            )
                            model.save(local_model_path)

                            # Create ZIP
                            with zipfile.ZipFile(
                                local_zip_path, "w", zipfile.ZIP_DEFLATED
                            ) as zipf:
                                for root, dirs, files in os.walk(
                                    local_model_path
                                ):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.relpath(
                                            file_path, local_model_path
                                        )
                                        zipf.write(file_path, arcname)

                            # Upload ZIP to stage
                            session.file.put(
                                local_zip_path,
                                STAGE_NAME,
                                overwrite=True,
                                auto_compress=False,
                            )
                            os.remove(local_zip_path)

                    except Exception as e:
                        model_source = f"INTERNET_DOWNLOAD_FALLBACK: {str(e)}"
                        model = SentenceTransformer(
                            model_name, cache_folder="/tmp/huggingface"
                        )
                        model.save(local_model_path)

                # Inference
                model = SentenceTransformer(local_model_path)
                embedding = model.encode(text_input).tolist()
                execution_time = time.time() - start_time

                return json.dumps(
                    {
                        "embedding": embedding,
                        "model_source": model_source,
                        "execution_time": execution_time,
                    }
                )

            except Exception as e:
                import traceback

                execution_time = time.time() - start_time
                return json.dumps(
                    {
                        "embedding": None,
                        "model_source": f"ERROR: {str(e)}",
                        "execution_time": execution_time,
                        "traceback": traceback.format_exc(),
                    }
                )

    def _setup_search_procedure(self) -> None:
        """Register the search_semantic stored procedure."""
        session = self.client.get_snowpark_session()
        embedding_model = self.embedding_model.value

        @sproc(
            session=session,
            name="VECTORS.search_semantic",
            packages=["snowflake-snowpark-python"],
            is_permanent=True,
            stage_location="@VECTORS.embedding_models_stage",
            replace=True,
            python_version="3.10",
        )
        def search_semantic(
            session: Session,
            query_text: str,
            embeddings_table: str,
            top_k: int = 10,
            filters: Optional[str] = None,
        ) -> list:
            """Execute semantic search with cosine similarity scoring."""
            import json
            import traceback

            try:
                # Get query embedding via embed_text_proc
                escaped_query = query_text.replace("'", "''")
                embedding_sql = f"CALL VECTORS.embed_text_proc('{escaped_query}', '{embedding_model}')"

                embedding_result = session.sql(embedding_sql).collect()
                if not embedding_result:
                    return []

                # Parse embedding result
                embedding_json = json.loads(embedding_result[0][0])
                query_embedding = embedding_json.get("embedding", [])
                embedding_values = ",".join(map(str, query_embedding))

                # Build search query with filtering and similarity calculation
                search_sql = f"""
                    WITH filtered_embeddings AS (
                        SELECT *
                        FROM {embeddings_table}
                        WHERE EMBEDDING IS NOT NULL
                """

                # Apply filters if provided
                if filters and filters.strip() and filters != "NULL":
                    search_sql += f" AND ({filters})"

                search_sql += f"""
                    )
                    SELECT
                        *,
                        VECTOR_COSINE_SIMILARITY(
                            EMBEDDING,
                            CAST(ARRAY_CONSTRUCT({embedding_values}) AS VECTOR(FLOAT, 768))
                        )::FLOAT AS COSINE_SIMILARITY_SCORE
                    FROM filtered_embeddings
                    ORDER BY COSINE_SIMILARITY_SCORE DESC
                    LIMIT {top_k}
                """

                # Execute search query
                results = session.sql(search_sql).collect()

                # Format results and convert datetime objects to ISO format strings
                result_list = []
                for row in results:
                    row_dict = row.as_dict()

                    # Convert datetime objects to ISO format for JSON serialization
                    for key, value in row_dict.items():
                        if hasattr(value, "isoformat"):
                            row_dict[key] = value.isoformat()

                    result_list.append(row_dict)

                return result_list

            except Exception as e:
                return [f"Error: {str(e)}\n{traceback.format_exc()}"]

    def search_semantic(
        self,
        query: str,
        embeddings_table: str = "VECTORS.RECIPES_50K_EMBEDDINGS",
        top_k: int = 10,
        filter_conditions: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute semantic search using server-side embedding generation.

        Encodes the query using the configured embedding model and finds the
        most similar documents using cosine similarity.

        Args:
            query: Search query text (plain text, not pre-computed embedding).
            embeddings_table: Name of the table containing embeddings.
                Defaults to "VECTORS.RECIPES_50K_EMBEDDINGS".
            top_k: Maximum number of results to return. Defaults to 10.
            filter_conditions: Optional SQL WHERE clause for filtering results.

        Returns:
            List of matching documents with cosine similarity scores, sorted
            by similarity in descending order. Returns empty list if no results
            found or on error.
        """
        # Escape single quotes for SQL safety
        safe_query = query.replace("'", "''")
        safe_table = embeddings_table.replace("'", "''")
        filter_param = "NULL"

        if filter_conditions:
            safe_filters = filter_conditions.replace("'", "''")
            filter_param = f"'{safe_filters}'"

        sql = f"CALL VECTORS.search_semantic('{safe_query}', '{safe_table}', {top_k}, {filter_param})"

        try:
            results = self.client.execute(sql, fetch="all")

            if not results:
                return []

            return json.loads(results[0][0])

        except (json.JSONDecodeError, IndexError, TypeError):
            return []
