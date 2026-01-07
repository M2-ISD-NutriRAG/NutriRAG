"""
Example usage of the SearchService for combined vector and BM25 search.
"""

import os
import sys

import pandas as pd
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.snowflake.client import SnowflakeClient
from app.services.search_service import SearchService
from app.models.search import SearchFilters, NumericFilter


def example_combined_search():
    """Example: Search using combined vector + BM25 search."""
    print("=== Combined Vector + BM25 Search (Hybrid) ===\n")

    try:
        client = SnowflakeClient()
        search_service = SearchService(client)

        query = "pasta with tomato"
        top_k = 10

        print(f"Query: {query}")
        print(f"Method: Combined (Vector + BM25)\n")

        results = search_service.search(
            query=query,
            limit=top_k,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        )

        print(f"Results found: {len(results)}\n")

        if results:
            # Check if results contain an error
            if isinstance(results[0], dict) and "error" in results[0]:
                print(f"Error from search: {results[0]['error']}")
                if "traceback" in results[0]:
                    print(f"Traceback: {results[0]['traceback']}")
                return

            DISPLAY_COLUMNS = [
                "ID",
                "COMBINED_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
                "BM25_SCORE",
                "COSINE_SIMILARITY_SCORE",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COMBINED_SCORE"] = df["COMBINED_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        import traceback

        print(f"Error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}\n")


def example_search_with_numeric_filters():
    """Example: Search with numeric filters (minutes, servings)."""
    print("=== Search with Numeric Filters ===\n")

    try:
        client = SnowflakeClient()
        search_service = SearchService(client)

        query = "quick healthy breakfast"
        top_k = 10

        # Create filters: recipes with <= 30 minutes
        filters = SearchFilters(
            numeric_filters=[
                NumericFilter(name="minutes", operator="<=", value=30)
            ]
        )

        print(f"Query: {query}")
        print(f"Filters: MINUTES <= 30")
        print(f"Method: Combined\n")

        results = search_service.search(
            query=query,
            filters=filters,
            limit=top_k,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        )

        print(f"Results found: {len(results)}\n")

        if results:
            DISPLAY_COLUMNS = [
                "COMBINED_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
                "BM25_SCORE",
                "COSINE_SIMILARITY_SCORE",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COMBINED_SCORE"] = df["COMBINED_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Error: {str(e)}\n")


def example_search_with_dietary_filters():
    """Example: Search with dietary tag filters."""
    print("=== Search with Dietary Filters ===\n")

    try:
        client = SnowflakeClient()
        search_service = SearchService(client)

        query = "protein rich meal"
        top_k = 10

        # Create filters: must contain vegetarian and gluten-free tags
        filters = SearchFilters(dietary_filters=["vegetarian"])

        print(f"Query: {query}")
        print(f"Filters: Must contain 'vegetarian' tag")
        print(f"Method: Combined\n")

        results = search_service.search(
            query=query,
            filters=filters,
            limit=top_k,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        )

        if results and isinstance(results, list):
            print(f"Results found: {len(results)}\n")
        else:
            print(f"Results found: 0\n")
            results = []

        if results:

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            DISPLAY_COLUMNS = [
                "COMBINED_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
                "BM25_SCORE",
                "COSINE_SIMILARITY_SCORE",
            ]

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]

            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COMBINED_SCORE"] = df["COMBINED_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Error: {str(e)}\n")


def example_search_with_ingredient_filters():
    """Example: Search with ingredient inclusion/exclusion filters."""
    print("=== Search with Ingredient Filters ===\n")

    try:
        client = SnowflakeClient()
        search_service = SearchService(client)

        query = "pasta dish"
        top_k = 10

        # Create filters: must include tomato, must exclude dairy
        filters = SearchFilters(
            include_ingredients=["tomato"],
            exclude_ingredients=["cheese", "cream"],
        )

        print(f"Query: {query}")
        print(f"Filters:")
        print(f"  - Must include: tomato")
        print(f"  - Must exclude: cheese, cream")
        print(f"Method: Combined\n")

        results = search_service.search(
            query=query,
            filters=filters,
            limit=top_k,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        )

        if results and isinstance(results, list):
            print(f"Results found: {len(results)}\n")
        else:
            print(f"Results found: 0\n")
            results = []

        if results:
            DISPLAY_COLUMNS = [
                "COMBINED_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
                "BM25_SCORE",
                "COSINE_SIMILARITY_SCORE",
            ]

            def truncate(text, max_len=80):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COMBINED_SCORE"] = df["COMBINED_SCORE"].apply(
                lambda x: f"{float(x):.4f}"
            )

            print(
                tabulate(
                    df, headers="keys", tablefmt="rounded_grid", showindex=False
                )
            )

    except Exception as e:
        print(f"Error: {str(e)}\n")


def example_search_with_multiple_filters():
    """Example: Search with multiple filter types combined."""
    print("=== Search with Multiple Filters ===\n")

    try:
        client = SnowflakeClient()
        search_service = SearchService(client)

        query = "light dinner"
        top_k = 10

        # Create filters: multiple criteria
        filters = SearchFilters(
            numeric_filters=[
                NumericFilter(name="minutes", operator="<=", value=45),
            ],
            dietary_filters=["vegetarian"],
            include_ingredients=["vegetables"],
            exclude_ingredients=["meat", "fish"],
        )

        print(f"Query: {query}")
        print(f"Filters:")
        print(f"  - MINUTES <= 45")
        print(f"  - Must contain tag: vegetarian")
        print(f"  - Must include ingredient: vegetables")
        print(f"  - Must exclude ingredients: meat, fish")
        print(f"Method: Combined\n")

        results = search_service.search(
            query=query,
            filters=filters,
            limit=top_k,
            index_table="VECTORS.RECIPES_SAMPLE_50K_BM25_INDEX",
            source_table="ENRICHED.RECIPES_SAMPLE_50K",
            embeddings_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        )

        if results and isinstance(results, list):
            print(f"Results found: {len(results)}\n")
        else:
            print(f"Results found: 0\n")
            results = []

        if results:
            DISPLAY_COLUMNS = [
                "COMBINED_SCORE",
                "NAME",
                "MINUTES",
                "DESCRIPTION",
                "FILTERS",
                "BM25_SCORE",
                "COSINE_SIMILARITY_SCORE",
            ]

            def truncate(text, max_len=60):
                if isinstance(text, str):
                    text = text.replace("\n", " ")
                    return text[:max_len] + "…" if len(text) > max_len else text
                return text

            df = pd.DataFrame(results)[DISPLAY_COLUMNS]
            df["DESCRIPTION"] = df["DESCRIPTION"].apply(truncate)
            df["COMBINED_SCORE"] = df["COMBINED_SCORE"].apply(
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
    print("\n" + "=" * 100)
    print("INITIALIZING SEARCH SERVICE WITH SETUP")
    print("=" * 100 + "\n")
    # Initialize SearchService with Snowflake client
    _ = SearchService(SnowflakeClient(), setup=True)

    print("\n" + "=" * 100)
    print("SEARCH SERVICE EXAMPLES - COMBINED VECTOR + BM25 HYBRID SEARCH")
    print("=" * 100 + "\n")

    # Example 1: Combined Search
    print("Example 1: Combined Vector + BM25 Search (Hybrid)")
    print("-" * 100)
    example_combined_search()

    print("\n" + "-" * 100 + "\n")

    # Example 2: Numeric Filters
    print("Example 2: Search with Numeric Filters")
    print("-" * 100)
    example_search_with_numeric_filters()

    print("\n" + "-" * 100 + "\n")

    # Example 3: Dietary Filters
    print("Example 3: Search with Dietary Filters")
    print("-" * 100)
    example_search_with_dietary_filters()

    print("\n" + "-" * 100 + "\n")

    # Example 4: Ingredient Filters
    print("Example 4: Search with Ingredient Filters")
    print("-" * 100)
    example_search_with_ingredient_filters()

    print("\n" + "-" * 100 + "\n")

    # Example 5: Multiple Filters
    print("Example 5: Search with Multiple Filters Combined")
    print("-" * 100)
    example_search_with_multiple_filters()

    print("=" * 100 + "\n")
