"""
BM25 Search Service Module.

This module provides BM25-based full-text search capabilities integrated with
Snowflake. It handles index creation, serialization, and searching with optional
filtering support.
"""

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional

from snowflake.snowpark import Session
from snowflake.snowpark.functions import sproc

from shared.snowflake.client import SnowflakeClient


class BM25Service:
    """
    BM25 Full-Text Search Service.

    Manages BM25 index creation, serialization, and searching on Snowflake.
    Provides functionality to build indexes from source tables and execute
    searches with optional filtering conditions.

    Attributes:
        client: Snowflake client for database operations.
    """

    def __init__(
        self, snowflake_client: SnowflakeClient, setup: bool = False
    ):
        """
        Initialize the BM25 Service.

        Args:
            snowflake_client: SnowflakeClient instance.
            setup: If True, uploads utility files and registers stored procedures.
        """
        self.client = snowflake_client
        if setup:
            self._upload_utils_to_stage()
            self._setup_procedures()

    def _upload_utils_to_stage(self) -> None:
        """Upload utility files and dependencies to Snowflake stage."""
        try:
            self.client.execute(
                "CREATE STAGE IF NOT EXISTS VECTORS.bm25_stage DIRECTORY = (ENABLE = true)"
            )
        except Exception as e:
            # Stage may already exist; proceed with upload
            pass

        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_path = os.path.join(current_dir, "..", "utils", "bm25_utils.py")

        if not os.path.exists(utils_path):
            raise FileNotFoundError(f"bm25_utils.py not found at {utils_path}")

        rank_lib_path = os.path.join(current_dir, "rank_bm25.py")
        rank_url = "https://raw.githubusercontent.com/dorianbrown/rank_bm25/master/rank_bm25.py"

        try:
            urllib.request.urlretrieve(rank_url, rank_lib_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download rank_bm25.py: {e}")

        files_to_upload = [utils_path, rank_lib_path]

        try:
            for local_path in files_to_upload:
                if not os.path.exists(local_path):
                    continue

                abs_path = os.path.abspath(local_path).replace("\\", "/")

                put_sql = f"""
                PUT 'file://{abs_path}'
                @VECTORS.bm25_stage
                AUTO_COMPRESS = FALSE
                OVERWRITE = TRUE
                """
                self.client.execute(put_sql)

        except Exception as e:
            raise RuntimeError(f"Failed to upload files to stage: {str(e)}")
        finally:
            if os.path.exists(rank_lib_path):
                try:
                    os.remove(rank_lib_path)
                except:
                    pass

    def _setup_procedures(self) -> None:
        """Register BM25 stored procedures in Snowflake."""
        self._register_build_bm25_index_procedure()
        self._register_search_bm25_procedure()

    def _register_build_bm25_index_procedure(self) -> None:
        """Register the build_bm25_index stored procedure."""
        session = self.client.get_snowpark_session()

        @sproc(
            session=session,
            name="VECTORS.build_bm25_index",
            packages=["numpy", "snowflake-snowpark-python"],
            is_permanent=True,
            stage_location="@VECTORS.bm25_stage",
            imports=[
                "@VECTORS.bm25_stage/bm25_utils.py",
                "@VECTORS.bm25_stage/rank_bm25.py",
            ],
            replace=True,
            external_access_integrations=["training_internet_access"],
            python_version="3.10",
        )
        def build_bm25_index(
            session: Session,
            source_table: str,
            text_columns: list,
            id_column: str,
            index_table: str,
            field_weights: Optional[str] = None,
        ) -> str:
            """
            Build BM25 index from source table.

            Creates a BM25 index from the specified text columns in the source table,
            saves the index mapping, and persists the serialized index to Snowflake stage.

            Args:
                session: Snowflake Snowpark session.
                source_table: Name of the source table containing documents.
                text_columns: List of column names to index.
                id_column: Column name containing document IDs.
                index_table: Name of the table to store index mappings.
                field_weights: Optional JSON string of field weights for ranking.

            Returns:
                Success message with index information or error details.
            """
            import json
            import io
            from datetime import datetime
            import traceback

            import bm25_utils

            try:
                # Load documents from source table
                columns = [id_column] + text_columns
                rows = session.table(source_table).select(columns).collect()
                documents = [row.as_dict() for row in rows]

                # Parse field weights if provided
                weights_dict = None
                if (
                    field_weights
                    and field_weights.strip()
                    and field_weights != "NULL"
                ):
                    weights_dict = json.loads(field_weights)

                # Build BM25 index
                bm25, doc_ids, corpus = bm25_utils.build_bm25_index(
                    documents=documents,
                    text_fields=text_columns,
                    id_field=id_column,
                    field_weights=weights_dict,
                )

                # Save index mapping table (DOC_ID <-> DOC_INDEX)
                index_data = []
                for idx, (doc_id, tokens) in enumerate(zip(doc_ids, corpus)):
                    index_data.append(
                        {
                            "DOC_ID": doc_id,
                            "DOC_INDEX": idx,
                            "TOKENS": tokens,
                            "TOKEN_COUNT": len(tokens),
                        }
                    )
                session.create_dataframe(index_data).write.mode(
                    "overwrite"
                ).save_as_table(index_table)

                # Serialize BM25 object and persist to stage
                bm25_serialized = bm25_utils.serialize_bm25(bm25)
                data_bytes = bm25_serialized.encode("utf-8")
                file_handle = io.BytesIO(data_bytes)

                index_filename = f"{index_table}.bm25"
                session.file.put_stream(
                    file_handle,
                    f"@VECTORS.bm25_stage/{index_filename}",
                    overwrite=True,
                    auto_compress=False,
                )

                # Save index metadata
                bm25_table = f"{index_table}_BM25"
                bm25_metadata = [
                    {
                        "INDEX_FILE_PATH": f"@VECTORS.bm25_stage/{index_filename}",
                        "NUM_DOCS": len(doc_ids),
                        "CREATED_AT": datetime.utcnow(),
                    }
                ]
                session.create_dataframe(bm25_metadata).write.mode(
                    "overwrite"
                ).save_as_table(bm25_table)

                return f"Index created: {len(doc_ids)} docs. File: @VECTORS.bm25_stage/{index_filename}"

            except Exception as e:
                return f"Error: {str(e)}\n{traceback.format_exc()}"

    def _register_search_bm25_procedure(self) -> None:
        """Register the search_bm25 stored procedure."""
        session = self.client.get_snowpark_session()

        @sproc(
            session=session,
            name="VECTORS.search_bm25",
            packages=["numpy", "snowflake-snowpark-python"],
            is_permanent=True,
            stage_location="@VECTORS.bm25_stage",
            imports=[
                "@VECTORS.bm25_stage/bm25_utils.py",
                "@VECTORS.bm25_stage/rank_bm25.py",
            ],
            replace=True,
            external_access_integrations=["training_internet_access"],
            python_version="3.10",
        )
        def search_bm25(
            session: Session,
            search_query: str,
            index_table: str,
            source_table: str,
            top_k: int,
            filter_conditions: Optional[str] = None,
        ) -> list:
            """
            Execute BM25 semantic search with optional filtering.

            Searches the BM25 index for documents matching the query, applies
            optional filters, and returns results sorted by BM25 relevance score.

            Args:
                session: Snowflake Snowpark session.
                search_query: Search query string.
                index_table: Name of the index mapping table.
                source_table: Name of the source table to retrieve results from.
                top_k: Number of top results to return.
                filter_conditions: Optional SQL WHERE clause for filtering results.

            Returns:
                List of matching documents with BM25 scores, sorted by relevance.
            """
            import io
            import traceback

            import bm25_utils

            try:
                # Apply SQL filters to identify valid document IDs
                filter_where = ""
                if (
                    filter_conditions
                    and filter_conditions.strip()
                    and filter_conditions != "NULL"
                ):
                    filter_where = f"WHERE {filter_conditions}"

                valid_ids_result = session.sql(
                    f"SELECT DISTINCT ID FROM {source_table} {filter_where}"
                ).collect()
                valid_ids = {r["ID"] for r in valid_ids_result}

                if not valid_ids:
                    return []

                # Load document ID to index mapping
                index_rows = session.sql(
                    f"""
                    SELECT DOC_ID, DOC_INDEX
                    FROM {index_table}
                    ORDER BY DOC_INDEX
                    """
                ).collect()

                filtered_doc_ids = []
                filtered_offsets = []

                for r in index_rows:
                    doc_id = r["DOC_ID"]
                    if doc_id in valid_ids:
                        filtered_doc_ids.append(doc_id)
                        filtered_offsets.append(r["DOC_INDEX"])

                if not filtered_doc_ids:
                    return []

                # Load BM25 index from stage
                bm25_table = f"{index_table}_BM25"
                meta_result = session.sql(
                    f"SELECT INDEX_FILE_PATH FROM {bm25_table} LIMIT 1"
                ).collect()

                if not meta_result:
                    return []

                file_path = meta_result[0]["INDEX_FILE_PATH"]
                input_stream = session.file.get_stream(file_path)

                with io.BytesIO(input_stream.read()) as f:
                    bm25_data_str = f.read().decode("utf-8")

                bm25 = bm25_utils.deserialize_bm25(bm25_data_str)

                # Calculate BM25 scores for query
                query_tokens = bm25_utils.tokenize(search_query)
                scores = bm25.get_batch_scores(query_tokens, filtered_offsets)

                # Associate document IDs with scores and sort by relevance
                scored_results = sorted(
                    zip(filtered_doc_ids, scores),
                    key=lambda x: x[1],
                    reverse=True,
                )[:top_k]

                if not scored_results:
                    return []

                # Retrieve full document data from source table
                doc_ids_str = "', '".join(
                    str(doc_id) for doc_id, _ in scored_results
                )

                result_df = session.sql(
                    f"""
                    SELECT * FROM {source_table}
                    WHERE ID IN ('{doc_ids_str}')
                    """
                )
                result_rows = result_df.collect()

                # Add BM25 scores to results and format for JSON serialization
                score_map = {
                    doc_id: float(score) for doc_id, score in scored_results
                }
                result_list = []

                for row in result_rows:
                    row_dict = row.as_dict()
                    row_dict["BM25_SCORE"] = score_map.get(row_dict["ID"], 0.0)

                    # Convert datetime objects to ISO format strings
                    for key, value in row_dict.items():
                        if hasattr(
                            value, "isoformat"
                        ):  # datetime.date and datetime.datetime
                            row_dict[key] = value.isoformat()

                    result_list.append(row_dict)

                # Sort results by BM25 score in descending order
                result_list.sort(key=lambda x: x["BM25_SCORE"], reverse=True)

                return result_list

            except Exception as e:
                return [f"Error: {str(e)}\n{traceback.format_exc()}"]

    def build_index(
        self,
        source_table: str,
        text_columns: List[str],
        id_column: str = "ID",
        field_weights: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Launch BM25 index creation on Snowflake.

        Args:
            source_table: Name of the source table containing documents.
            text_columns: List of column names to include in the index.
            id_column: Column name containing unique document identifiers.
                Defaults to "ID".
            field_weights: Optional dictionary of field weights for scoring.

        Returns:
            Dictionary containing:
                - message: Status message or error details.
                - index_table: Name of the created index mapping table.
                - metadata_table: Name of the created metadata table.
                - field_weights: Field weights used in index creation.
        """
        cols_json = json.dumps(text_columns)

        if field_weights:
            weights_json = json.dumps(field_weights)
            weights_param = f"'{weights_json}'"
        else:
            weights_param = "NULL"

        base_name = source_table.split(".")[-1].replace('"', "")
        index_table = f"VECTORS.{base_name}_BM25_INDEX"

        query = f"CALL VECTORS.build_bm25_index('{source_table}', PARSE_JSON('{cols_json}'), '{id_column}', '{index_table}', {weights_param})"
        result = self.client.execute(query, fetch="one")

        return {
            "message": result[0] if result else "Success",
            "index_table": index_table,
            "metadata_table": f"{index_table}_BM25",
            "field_weights": field_weights,
        }

    def search(
        self,
        query: str,
        index_table: str,
        source_table: str,
        top_k: int = 10,
        filter_conditions: Optional[str] = None,
    ) -> List[Dict]:
        """
        Execute BM25 search query.

        Searches the BM25 index with optional filtering and returns ranked results.

        Args:
            query: Search query string.
            index_table: Name of the index mapping table.
            source_table: Name of the source table to retrieve results from.
            top_k: Maximum number of results to return. Defaults to 10.
            filter_conditions: Optional SQL WHERE clause for filtering results.

        Returns:
            List of matching documents with BM25 scores, sorted by relevance
            in descending order. Returns empty list if no results found or on error.
        """
        safe_query = query.replace("'", "''")
        if filter_conditions:
            safe_filters = filter_conditions.replace("'", "''")
            filter_param = f"'{safe_filters}'"
        else:
            filter_param = "NULL"

        sql = f"CALL VECTORS.search_bm25('{safe_query}', '{index_table}', '{source_table}', {top_k}, {filter_param})"
        results = self.client.execute(sql, fetch="all")

        if not results:
            return []

        try:
            return json.loads(results[0][0])
        except (json.JSONDecodeError, IndexError, TypeError):
            return []
