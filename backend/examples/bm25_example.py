"""
Example usage of the BM25Service for indexing and searching recipes.

Demonstrates creating BM25 indices on Snowflake and performing full-text searches
with optional SQL filtering on the recipe dataset.
"""

import os
import sys
import json

import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.snowflake.client import SnowflakeClient
from app.services.bm25_service import BM25Service


def example_build_index():
    """Build BM25 index on Snowflake with field weights.

    Demonstrates creating a BM25 full-text search index from the recipes table
    with custom field weights to prioritize NAME and DESCRIPTION fields.
    """
    print("=== BM25 Index Creation (Snowflake Execution) ===\n")

    try:
        # Initialize the service
        client = SnowflakeClient()
        bm25_service = BM25Service(client, setup=True)

        # Create the index with field weights
        result = bm25_service.build_index(
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

        print(f"{result['message']}")
        print(f"  - Index table: {result['index_table']}")
        print(f"  - Metadata table: {result['metadata_table']}\n")

    except Exception as e:
        print(f"Error: {str(e)}\n")


def example_search():
    """Perform BM25 search on the recipe index.

    Demonstrates a simple BM25 search query returning the top-5 results
    based on relevance scores.
    """
    print("=== BM25 Search (Snowflake Execution) ===\n")

    try:
        # Initialize the service
        client = SnowflakeClient()
        bm25_service = BM25Service(client)

        # Execute the search
        query = "chocolate cake"
        top_k = 5

        print(f"Query: {query}")
        print(f"Top_k: {top_k}\n")

        result = bm25_service.search(
            query=query,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            top_k=top_k,
        )

        print(f"Results found: {len(result)}\n")

        if result:
            DISPLAY_COLUMNS = [
                "BM25_SCORE",
                "ID",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "TAGS",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(result)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Erro: {str(e)}\n")


def example_search_with_filter():
    """Perform BM25 search with SQL filter constraints.

    Demonstrates filtering search results to recipes with preparation time
    <= 30 minutes using SQL WHERE clause.
    """
    print("=== BM25 Search with Filters (Snowflake Execution) ===\n")

    try:
        # Initialize the service
        client = SnowflakeClient()
        bm25_service = BM25Service(client)

        # Execute search with time constraint
        query = "chocolate cake"
        top_k = 5
        filter_conditions = "MINUTES <= 30"

        print(f"Query: {query}")
        print(f"Top_k: {top_k}")
        print(f"Filter conditions: {filter_conditions}\n")

        result = bm25_service.search(
            query=query,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            top_k=top_k,
            filter_conditions=filter_conditions,
        )

        print(f"Results found: {len(result)}\n")

        if result:
            DISPLAY_COLUMNS = [
                "BM25_SCORE",
                "ID",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "TAGS",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(result)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Erreur: {str(e)}\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BM25 SERVICE USAGE EXAMPLES")
    print("=" * 60 + "\n")

    # Run the examples
    example_build_index()
    example_search()
    example_search_with_filter()

    print("=" * 60)
    print("END OF EXAMPLES")
    print("=" * 60 + "\n")
