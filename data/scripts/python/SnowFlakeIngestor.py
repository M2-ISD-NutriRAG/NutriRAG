import ast
import logging
import os
import pandas as pd
import numpy as np

from config import CACHE_DIR, DATA_PARAMS, OUTPUT_FILES, SNOWFLAKE_CONFIG
from DataTransformer import DataTransformer
from SnowflakeConnector import SnowflakeConnector

class SnowflakeIngestor:
    """Orchestrates the ingestion process into Snowflake."""

    def __init__(self, connector: SnowflakeConnector, transformer: DataTransformer):
        self.connector = connector
        self.transformer = transformer
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_ingestion(self):
        # ==================================================================================
        # 1. READ BASE TABLE (RAW_RECIPES)
        # ==================================================================================
        self.logger.info("Reading BASE RAW table (raw_recipes) into pandas...")
        table_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['raw_table']}"
        df = self.connector.session.table(table_path)
        recipes = df.to_pandas()
        
        # SÉCURITÉ : On force tout en MAJUSCULES pour éviter les erreurs de casse
        recipes.columns = [c.upper() for c in recipes.columns]

        # NETTOYAGE PRÉALABLE : Si HAS_IMAGE ou IMAGE_URL existent déjà (pollution), on les vire
        # pour éviter la création de colonnes HAS_IMAGE_x / HAS_IMAGE_y lors du merge
        cols_to_drop = [c for c in ["HAS_IMAGE", "IMAGE_URL"] if c in recipes.columns]
        if cols_to_drop:
            self.logger.info(f"Dropping existing columns in base table to avoid merge conflicts: {cols_to_drop}")
            recipes = recipes.drop(columns=cols_to_drop)
        
        # ==================================================================================
        # 2. LOAD & PROCESS IMAGES (FROM RECIPES_ENHANCED_V2)
        # ==================================================================================
        self.logger.info("Reading IMAGES table (recipes_enhanced_v2)...")
        img_table_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_enhanced_v2_table']}"
        df_img_snowflake = self.connector.session.table(img_table_path)
        
        pdf_img = df_img_snowflake.to_pandas()
        pdf_img.columns = [c.lower() for c in pdf_img.columns]
        
        # Initialisation du DataFrame image propre
        df_img = pd.DataFrame()
        df_img["id"] = pdf_img["id"]
        
        if "images" in pdf_img.columns:
            # Nettoyage: String "['url']" -> List ['url'] -> String "url"
            # 1. Parse la liste
            pdf_img["images_parsed"] = pdf_img["images"].apply(self.transformer.safe_parse_list)
            
            # 2. Extraction de la première URL
            df_img["IMAGE_URL"] = pdf_img["images_parsed"].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None
            )
            # 3. Calcul HAS_IMAGE (1 ou 0)
            df_img["HAS_IMAGE"] = df_img["IMAGE_URL"].apply(lambda x: 1 if x is not None else 0)
        else:
            self.logger.warning("Colonne 'images' absente. Images ignorées.")
            df_img["HAS_IMAGE"] = 0
            df_img["IMAGE_URL"] = None

        # On ne garde que l'essentiel et on renomme pour le merge
        df_img = df_img[["id", "HAS_IMAGE", "IMAGE_URL"]].rename(columns={"id": "ID"})

        # ==================================================================================
        # 3. LOAD QUANTITY/SEARCH TERMS (RECIPES_W_SEARCH_TERMS)
        # ==================================================================================
        self.logger.info("Reading Quantity/Search Terms table...")
        recipes_w_search_terms_table = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_w_search_terms_table']}"
        df_quantity_snowflake = self.connector.session.table(recipes_w_search_terms_table)
        
        pdf_quantity = df_quantity_snowflake.to_pandas()
        pdf_quantity.columns = [c.lower() for c in pdf_quantity.columns]
        
        df_quantity = pdf_quantity[["id", "ingredients_raw_str", "serving_size", 'servings', 'search_terms']].copy()
        
        # Nettoyage serving_size: "1 (155 g)" -> "155"
        df_quantity["serving_size"] = df_quantity["serving_size"].astype(str).apply(
            lambda x: x[3:-3] if len(x) > 6 else None
        )
        # Nettoyage search_terms
        df_quantity["search_terms"] = df_quantity["search_terms"].astype(str).apply(
            lambda x: x.replace("{", "[").replace("}", "]")
        )

        # Majuscules pour le merge
        df_quantity.columns = [c.upper() for c in df_quantity.columns]

        # ==================================================================================
        # 4. MERGE ALL TABLES
        # ==================================================================================
        self.logger.info("Merging BASE + IMAGES + QUANTITY tables...")
        
        # Merge 1: Base + Images (Left Join)
        recipes = recipes.merge(df_img, how="left", on="ID")
        
        # DEBUG : Vérification post-merge 1
        if "HAS_IMAGE" not in recipes.columns:
            self.logger.error(f"COLONNE HAS_IMAGE MANQUANTE APRÈS MERGE 1. Colonnes présentes : {list(recipes.columns)}")
            # Fallback d'urgence pour éviter le crash
            recipes["HAS_IMAGE"] = 0
            recipes["IMAGE_URL"] = None

        # Merge 2: + Quantity (Inner Join)
        recipes = recipes.merge(df_quantity, how="inner", on="ID")

        # ==================================================================================
        # 5. NORMALIZE & CLEAN
        # ==================================================================================
        # Parse nutrition
        recipes["NUTRITION"] = recipes["NUTRITION"].apply(
            lambda x: x if isinstance(x, list) else (ast.literal_eval(x) if (x is not None and x != "") else [])
        )

        # Parse other list columns
        list_columns = ["TAGS", "STEPS", "INGREDIENTS", "SEARCH_TERMS", "INGREDIENTS_RAW_STR"]
        for col in list_columns:
            if col in recipes.columns:
                recipes[col] = recipes[col].apply(self.transformer.safe_parse_list)

        # Convert SERVING_SIZE to numeric
        if "SERVING_SIZE" in recipes.columns:
            recipes["SERVING_SIZE"] = pd.to_numeric(recipes["SERVING_SIZE"], errors='coerce')
            
        # Remplir les valeurs manquantes pour les images (fillna safe)
        if "HAS_IMAGE" in recipes.columns:
            recipes["HAS_IMAGE"] = recipes["HAS_IMAGE"].fillna(0)
        
        # ==================================================================================
        # 6. APPLY FILTERS
        # ==================================================================================
        self.logger.info("Applying filters...")
        clean_data = recipes[
            (recipes["NAME"].notna()) &
            (recipes["NAME"].apply(lambda x: len(str(x)) > 0)) &
            (recipes["MINUTES"] > DATA_PARAMS["min_minutes"]) &
            (recipes["ID"].notna()) &
            (recipes["SUBMITTED"].notna()) &
            (recipes["TAGS"].apply(lambda x: len(x) > 0)) &
            (recipes["NUTRITION"].apply(lambda x: len(x) == 7)) &
            (recipes["DESCRIPTION"].notna()) &
            (recipes["STEPS"].apply(lambda x: len(x) > 0)) &
            (recipes["INGREDIENTS"].apply(lambda x: len(x) > 0))
        ].copy()

        row_count = len(clean_data)
        if row_count == 0:
            raise ValueError("No rows remain after filtering; cannot sample or ingest.")

        # ==================================================================================
        # 7. SAMPLING & SCHEMA DEFINITION
        # ==================================================================================
        sample_size = min(DATA_PARAMS["sample_size"], row_count)
        clean_data = clean_data.sample(n=sample_size, random_state=DATA_PARAMS["random_seed"]).reset_index(drop=True)

        clean_data["FILTERS"] = clean_data["TAGS"].apply(lambda x: [])

        # Define table schema
        columns_spec = {
            "NAME": "VARCHAR(16777216)",
            "ID": "NUMBER(38,0)",
            "MINUTES": "NUMBER(38,0)",
            "CONTRIBUTOR_ID": "NUMBER(38,0)",
            "SUBMITTED": "TIMESTAMP_NTZ",
            "TAGS": "ARRAY",
            "NUTRITION": "ARRAY",
            "N_STEPS": "NUMBER(38,0)",
            "STEPS": "ARRAY",
            "DESCRIPTION": "VARCHAR(16777216)",
            "INGREDIENTS": "ARRAY",
            "N_INGREDIENTS": "NUMBER(38,0)",
            "HAS_IMAGE": "NUMBER(38,0)",
            "IMAGE_URL": "VARCHAR(16777216)",
            "INGREDIENTS_RAW_STR": "ARRAY",
            "SERVING_SIZE": "NUMBER(38,0)",
            "SERVINGS": "NUMBER(38,0)",
            "SEARCH_TERMS": "ARRAY",
            "FILTERS": "ARRAY",
        }
        
        cols_to_keep = [c for c in columns_spec.keys() if c in clean_data.columns]
        clean_data = clean_data[cols_to_keep]

        # ==================================================================================
        # 8. WRITE TO SNOWFLAKE
        # ==================================================================================
        self.logger.info(f"Writing {len(clean_data)} rows to CLEANED table...")
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(clean_data, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        # Write dev sample
        dev_sample_size = min(DATA_PARAMS["dev_sample_size"], len(clean_data))
        dev_data = clean_data.sample(n=dev_sample_size, random_state=DATA_PARAMS["random_seed"]).reset_index(drop=True)
        
        self.logger.info(f"Writing {len(dev_data)} rows to DEV table...")
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(dev_data, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        self.logger.info("Ingestion finished.")