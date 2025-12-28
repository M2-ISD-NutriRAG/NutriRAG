"""
Configuration file for NutriRAG data processing pipeline.
Contains all constants, file IDs, dataset names, and database configurations.
"""

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
    "raw_interactions": "RAW_INTERACTIONS.csv",
    "cleaned_ingredients": "CLEANED_INGREDIENTS.csv",
    "recipes_images": "recipes_enhanced_v2.csv",
    "recipes_w_search_terms": "recipes_w_search_terms.csv",
    "cleaned_recipes": "clean_recipes_to_snowflake.csv",
    "db_inserts": "clean_recipes_inserts.sql",
    "ingredients_parsing": "ingredients_parsing.csv",
}

# Database configuration
SNOWFLAKE_CONFIG = {
    "database": "NUTRIRAG_PROJECT",
    "raw_schema": "RAW",
    "cleaned_schema": "CLEANED",
    "dev_schema": "DEV_SAMPLE",
    "raw_table": "RAW_RECIPES_110K",
    "cleaned_table": "RECIPES_SAMPLE_50K",
    "recipes_enhanced_v2_table": "RECIPES_ENHANCED_V2",
    "recipes_w_search_terms_table": "RECIPES_W_SEARCH_TERMS",
    "ingredients_parsing_table": "INGREDIENTS_QUANTITY",
}

# Data processing parameters
DATA_PARAMS = {
    "sample_size": 50000,
    "dev_sample_size": 1000,
    "random_seed": 42,
    "min_minutes": 5,
}

# Cache directory
CACHE_DIR = "./dataset"
TEMP_KAGGLE_CACHE_DIR = "./temp_kaggle_cache"

# SQL DIR
SQL_DIR = "./data/scripts/sql"
