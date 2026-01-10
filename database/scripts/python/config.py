"""
Configuration file for NutriRAG data processing pipeline.
Contains all constants, file IDs, dataset names, and database configurations.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the absolute path to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Output filenames
OUTPUT_FILES = {
    "cleaned_ingredients": "cleaned_ingredients.csv",
    "cleaned_recipes": "Recipes_50k.csv",
    "ingredients_with_clusters": "ingredients_with_clusters.csv",
    "tagged" : "tagged.csv",
    "parsing":"parsing.csv",
    "matching":"matching.csv"
}

# Database configuration
SNOWFLAKE_CONFIG = {
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "NUTRIRAG_PROJECT"),
    "database": os.getenv("SNOWFLAKE_DATABASE", "NUTRIRAG_PROJECT"),
    "raw_schema": "RAW",
    "analytics_schema": "ANALYTICS",
    "cleaned_schema": "CLEANED",
    "enriched_schema": "ENRICHED",
    "dev_schema": "DEV_SAMPLE",
    "cleaned_table": "RECIPES_SAMPLE_50K",
    "ingredients_parsing_table": "INGREDIENTS_QUANTITY",
    "ingredients_with_clusters_table": "INGREDIENTS_WITH_CLUSTERS",
    "tagged" : "INGREDIENTS_TAGGED",
    "parsing":"INGREDIENTS_QUANTITY",
    "matching":"INGREDIENTS_MATCHING"
}

# Data processing parameters
DATA_PARAMS = {
    "sample_size": 50000,
    "dev_sample_size": 1000,
    "random_seed": 42,
    "min_minutes": 5,
}

# Absolute paths
CACHE_DIR = os.path.join(PROJECT_ROOT, "dataset")
TEMP_KAGGLE_CACHE_DIR = os.path.join(PROJECT_ROOT, "temp_kaggle_cache")
SQL_DIR = os.path.join(PROJECT_ROOT, "database", "scripts", "sql")
