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

# Google Drive file IDs
GOOGLE_DRIVE_FILES = {
    "raw_recipes": "1fxvf7ghbgH0xkvHkPFM_K8_JbeL9QX3L",
    "raw_interactions": "10zdNLf2oKiMY30ZacdwdF1AEpkrbyoUN",
    "cleaned_ingredients": "1HjT5RiZnxlg2PkcMLlqzxBjeeRGITYvx",
}

# Kaggle dataset identifiers
KAGGLE_DATASETS = {
    "recipes_images": "behnamrahdari/foodcom-enhanced-recipes-with-images",
    "recipes_w_search_terms": "shuyangli94/foodcom-recipes-with-search-terms-and-tags",
}

# Output filenames
OUTPUT_FILES = {
    "raw_recipes": "RAW_recipes.csv",
    "raw_interactions": "RAW_interactions.csv",
    "cleaned_ingredients": "cleaned_ingredients.csv",
    "recipes_images": "recipes_enhanced_v2.csv",
    "recipes_w_search_terms": "recipes_w_search_terms.csv",
    "cleaned_recipes": "clean_recipes_to_snowflake.csv",
    "db_inserts": "clean_recipes_inserts.sql",
    "ingredients_parsing": "ingredients_parsing.csv",
    "ingredients_with_clusters": "ingredients_with_clusters.csv",
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
    "raw_table": "RAW_RECIPES_110K",
    "cleaned_table": "RECIPES_SAMPLE_50K",
    "recipes_enhanced_v2_table": "RECIPES_ENHANCED_V2",
    "recipes_w_search_terms_table": "RECIPES_W_SEARCH_TERMS",
    "ingredients_parsing_table": "INGREDIENTS_QUANTITY",
    "ingredients_with_clusters_table": "INGREDIENTS_WITH_CLUSTERS",
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
