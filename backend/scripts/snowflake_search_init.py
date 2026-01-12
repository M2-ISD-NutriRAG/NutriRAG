"""Script to initialize Snowflake search components."""

from shared import SnowflakeClient
from app.services import SearchService
from app.services import CreateVectorDatabaseService


def main():
    client = SnowflakeClient()

    # Initialize search service
    print("Initializing Search Service...")
    _ = SearchService(client, setup=True)
    print("Search Service initialized.")

    # Create vector database
    print("Creating Vector Database...")
    service = CreateVectorDatabaseService(
        client,
        source_table="ENRICHED.RECIPES_SAMPLE_50K",
        output_table="VECTORS.RECIPES_50K_EMBEDDINGS",
        id_column="ID",
        columns_to_embed=[
            "NAME",
            "TAGS",
            "SEARCH_TERMS",
            "INGREDIENTS",
            "DESCRIPTION",
        ],
        embedding_model="BAAI/bge-small-en-v1.5",
        setup=True,
    )

    service.create_vector_database()
    print("Vector Database created.")


if __name__ == "__main__":
    main()
