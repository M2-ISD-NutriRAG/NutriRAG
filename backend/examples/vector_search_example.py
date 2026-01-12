"""
Example usage of the Vector Search Service for semantic search.
"""

import os
import sys

import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.snowflake.client import SnowflakeClient
from app.services.vector_search_service import VectorSearchService


def setup_vector_search():
    """Setup vector search service and create all required procedures."""
    print("Setting up Vector Search Service...\n")

    try:
        client = SnowflakeClient()
        vector_service = VectorSearchService(client, setup=True)
        print("Vector Search Service setup completed successfully!\n")
        print("  - Stage: VECTORS.embedding_models_stage")
        print("  - Procedure: VECTORS.embed_text_proc")
        print("  - Procedure: VECTORS.search_semantic\n")
    except Exception as e:
        print(f"Error during setup: {str(e)}\n")
        raise


def example_semantic_search():
    """Example of semantic search"""
    print("=== Semantic Search ===\n")

    try:
        # Initialize the service
        client = SnowflakeClient()
        vector_service = VectorSearchService(client)

        # Perform semantic search
        query = "chocolate cake dessert"
        top_k = 5

        print(f"Query: {query}")
        print(f"Top_k: {top_k}")

        results = vector_service.search_semantic(
            query=query,
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
            top_k=top_k,
            embedding_model="BAAI/bge-small-en-v1.5",
        )

        print(f"Results found: {len(results)}\n")

        if results:
            DISPLAY_COLUMNS = [
                "COSINE_SIMILARITY_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COSINE_SIMILARITY_SCORE"] = df["COSINE_SIMILARITY_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Error: {str(e)}\n")


def example_semantic_search_with_filter():
    """Example of semantic search with SQL filters."""
    print("=== Semantic Search with Filters ===\n")

    try:
        # Initialize the service
        client = SnowflakeClient()
        vector_service = VectorSearchService(client)

        # Perform semantic search with filters
        query = "quick healthy breakfast"
        top_k = 5
        filter_conditions = "MINUTES <= 30"

        print(f"Query: {query}")
        print(f"Top_k: {top_k}")
        print(f"Filter: {filter_conditions}")

        results = vector_service.search_semantic(
            query=query,
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
            top_k=top_k,
            filter_conditions=filter_conditions,
            embedding_model="BAAI/bge-small-en-v1.5",
        )

        print(f"Results found: {len(results)}\n")

        if results:
            DISPLAY_COLUMNS = [
                "COSINE_SIMILARITY_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COSINE_SIMILARITY_SCORE"] = df["COSINE_SIMILARITY_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Error: {str(e)}\n")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("VECTOR SEARCH SERVICE EXAMPLES")
    print("=" * 80 + "\n")

    # Setup the service (creates procedures and stage)
    setup_vector_search()

    # Run examples
    print("Example 1: Semantic Search")
    print("-" * 80)
    example_semantic_search()

    print("\n" + "-" * 80 + "\n")

    print("Example 2: Semantic Search with Filters")
    print("-" * 80)
    example_semantic_search_with_filter()

    print("\n" + "=" * 80)
    print("END OF EXAMPLES")
    print("=" * 80 + "\n")
