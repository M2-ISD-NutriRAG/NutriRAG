import ast
import logging
import os
import pandas as pd
import numpy as np
from snowflake.snowpark.functions import col

from config import DATA_PARAMS, SNOWFLAKE_CONFIG, SQL_DIR
from DataTransformer import DataTransformer
from SnowflakeConnector import SnowflakeConnector

class SnowflakeIngestor:
    """Orchestrates the ingestion process into Snowflake."""

    def __init__(self, connector: SnowflakeConnector, transformer: DataTransformer):
        self.connector = connector
        self.transformer = transformer
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_ingestion_sql(self):
        """
        Server-side ingestion using SQL only.
        Much faster than loading everything to Pandas locally.
        """
        self.logger.info("=" * 60)
        self.logger.info("INGESTION: Server-side SQL processing")
        self.logger.info("=" * 60)

        try:
            # Load SQL template
            sql_path = os.path.join(SQL_DIR, "ingest_clean_recipes.sql")
            if not os.path.exists(sql_path):
                raise FileNotFoundError(f"Ingestion SQL not found: {sql_path}")
            
            self.logger.info(f"Loading SQL from: {sql_path}")
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_template = f.read()
            
            # Replace placeholders with actual config values
            sql = sql_template.format(
                database=SNOWFLAKE_CONFIG['database'],
                raw_schema=SNOWFLAKE_CONFIG['raw_schema'],
                cleaned_schema=SNOWFLAKE_CONFIG['cleaned_schema'],
                dev_schema=SNOWFLAKE_CONFIG['dev_schema'],
                raw_table=SNOWFLAKE_CONFIG['raw_table'],
                cleaned_table=SNOWFLAKE_CONFIG['cleaned_table'],
                recipes_enhanced_v2_table=SNOWFLAKE_CONFIG['recipes_enhanced_v2_table'],
                recipes_w_search_terms_table=SNOWFLAKE_CONFIG['recipes_w_search_terms_table']
            )
            
            # Split into statements and execute
            statements = []
            for stmt in sql.split(';'):
                # Remove comments and empty lines
                lines = []
                for line in stmt.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('--'):
                        lines.append(line)
                
                cleaned_stmt = ' '.join(lines).strip()
                if cleaned_stmt:
                    statements.append(cleaned_stmt)
            
            self.logger.info(f"Found {len(statements)} SQL statements to execute")
            
            for idx, stmt in enumerate(statements, 1):
                self.logger.info(f"Executing statement {idx}/{len(statements)}...")
                stmt_preview = stmt[:100].replace('\n', ' ')
                self.logger.debug(f"Statement: {stmt_preview}...")
                
                self.connector.safe_execute(stmt)
                self.logger.info(f"✅ Statement {idx} completed")
            
            self.logger.info("✅ Server-side ingestion completed successfully!")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            raise

    def run_ingestion(self):
        """Legacy Pandas-based ingestion. Use run_ingestion_sql() for better performance."""
        self.logger.info("🚀 Starting Ingestion Process with DETAILED DEBUGGING...")

        # ==================================================================================
        # 1. LOAD DATA & JOINS
        # ==================================================================================
        
        # --- A. Load Base Recipes ---
        self.logger.info("--- [STEP 1.A] Loading Base Recipes ---")
        table_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['raw_table']}"
        
        df_base_snow = self.connector.session.table(table_path)
        
        # Cast SUBMITTED to string to handle date formatting issues later in Pandas
        submitted_col = next((c for c in df_base_snow.columns if c.upper() == 'SUBMITTED'), None)
        if submitted_col:
            df_base_snow = df_base_snow.with_column(submitted_col, df_base_snow[submitted_col].astype("string"))

        recipes = df_base_snow.to_pandas()
        recipes.columns = [c.upper() for c in recipes.columns]
        
        self.logger.info(f"📊 [BASE] Rows loaded: {len(recipes)}") # LOG
        
        if "HAS_IMAGE" in recipes.columns: recipes = recipes.drop(columns=["HAS_IMAGE", "IMAGE_URL"])

        # --- B. Load & Prep Images ---
        self.logger.info("--- [STEP 1.B] Loading Images ---")
        img_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_enhanced_v2_table']}"
        
        df_img_snow = self.connector.session.table(img_path)
        cols_map = {c.lower(): c for c in df_img_snow.columns}
        id_col = cols_map.get('id', 'ID')
        img_col = cols_map.get('images', cols_map.get('image_url', 'IMAGES'))
        
        if img_col:
            pdf_img = df_img_snow.select(col(id_col), col(img_col)).to_pandas()
            pdf_img.columns = [c.lower() for c in pdf_img.columns]
            
            df_img = pd.DataFrame({"ID": pdf_img["id"]})
            target_col = "images" if "images" in pdf_img.columns else "image_url"
            
            parsed = pdf_img[target_col].apply(self.transformer.safe_parse_list)
            df_img["IMAGE_URL"] = parsed.apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
            df_img["HAS_IMAGE"] = df_img["IMAGE_URL"].apply(lambda x: 1 if x is not None else 0)
        else:
            pdf_ids = df_img_snow.select(col(id_col)).to_pandas()
            df_img = pd.DataFrame({"ID": pdf_ids[id_col.lower()]})
            df_img["HAS_IMAGE"] = 0
            df_img["IMAGE_URL"] = None
            
        self.logger.info(f"📊 [IMAGES] Rows loaded: {len(df_img)}") # LOG

        # --- C. Load & Prep Quantities ---
        self.logger.info("--- [STEP 1.C] Loading Quantities ---")
        qty_path = f"{SNOWFLAKE_CONFIG['database']}.{SNOWFLAKE_CONFIG['raw_schema']}.{SNOWFLAKE_CONFIG['recipes_w_search_terms_table']}"
        pdf_qty = self.connector.session.table(qty_path).to_pandas()
        pdf_qty.columns = [c.lower() for c in pdf_qty.columns]
        
        df_qty = pd.DataFrame({"ID": pdf_qty["id"]})
        if "serving_size" in pdf_qty.columns:
            df_qty["SERVING_SIZE"] = pdf_qty["serving_size"].astype(str)
        if "search_terms" in pdf_qty.columns:
             df_qty["SEARCH_TERMS"] = pdf_qty["search_terms"].astype(str).apply(lambda x: x.replace("{", "[").replace("}", "]"))
        if "ingredients_raw_str" in pdf_qty.columns:
            df_qty["INGREDIENTS_RAW_STR"] = pdf_qty["ingredients_raw_str"]
        if "servings" in pdf_qty.columns:
            df_qty["SERVINGS"] = pd.to_numeric(pdf_qty["servings"], errors='coerce')
            
        self.logger.info(f"📊 [QUANTITIES] Rows loaded: {len(df_qty)}") # LOG

        # --- D. Merging ---
        self.logger.info("--- [STEP 1.D] Merging Tables ---")
        
        # Merge 1: Images (Left Join)
        recipes = recipes.merge(df_img, how="left", on="ID")
        recipes["HAS_IMAGE"] = recipes["HAS_IMAGE"].fillna(0)
        self.logger.info(f"📊 Rows after Image Join (Left): {len(recipes)}") # LOG
        
        # Merge 2: Quantities (Inner Join) -> C'est souvent ici que ça casse !
        recipes = recipes.merge(df_qty, how="inner", on="ID")
        self.logger.info(f"📊 Rows after Quantity Join (Inner): {len(recipes)}") # LOG

        if len(recipes) == 0:
            self.logger.error("❌ CRITICAL: Rows dropped to 0 after Inner Join. Check ID matching between Base and Quantity tables.")
            return

        # ==================================================================================
        # 2. TRANSFORMATIONS
        # ==================================================================================
        self.logger.info("--- [STEP 2] Transformations ---")

        # Dates
        # if "SUBMITTED" in recipes.columns:
        #     recipes["SUBMITTED"] = recipes["SUBMITTED"].astype(str)
        #     recipes["SUBMITTED"] = pd.to_datetime(recipes["SUBMITTED"], format='%m/%d/%y', errors='coerce').dt.date
        #     # Check how many dates failed parsing
        #     valid_dates = recipes["SUBMITTED"].notna().sum()
        #     self.logger.info(f"📅 Valid Dates parsed: {valid_dates} / {len(recipes)}")

        # Minutes
        if "MINUTES" in recipes.columns:
            recipes["MINUTES"] = pd.to_numeric(recipes["MINUTES"], errors='coerce')

        # Nutrition
        recipes["NUTRITION"] = recipes["NUTRITION"].apply(
            lambda x: x if isinstance(x, list) else (ast.literal_eval(x) if (x is not None and x != "") else [])
        )
        
        # Lists parsing
        list_cols = ["TAGS", "STEPS", "INGREDIENTS", "SEARCH_TERMS", "INGREDIENTS_RAW_STR"]
        for col_name in list_cols:
            if col_name in recipes.columns:
                recipes[col_name] = recipes[col_name].apply(self.transformer.safe_parse_list)

        # ==================================================================================
        # 3. FILTRAGE (DEBUGGING GRANULAIRE)
        # ==================================================================================
        self.logger.info("--- [STEP 3] Filtering Analysis ---")
        
        total_rows = len(recipes)
        
        # Calcul des masques individuels pour voir qui tue les données
        mask_name = (recipes["NAME"].notna()) & (recipes["NAME"].apply(lambda x: len(str(x)) > 0))
        self.logger.info(f"🔎 Filter [NAME valid]: {mask_name.sum()} / {total_rows}")
        
        mask_minutes = recipes["MINUTES"] > 5
        self.logger.info(f"🔎 Filter [MINUTES > 5]: {mask_minutes.sum()} / {total_rows}")
        
        mask_id = recipes["ID"].notna()
        self.logger.info(f"🔎 Filter [ID valid]: {mask_id.sum()} / {total_rows}")
        
        mask_submitted = recipes["SUBMITTED"].notna()
        self.logger.info(f"🔎 Filter [SUBMITTED valid]: {mask_submitted.sum()} / {total_rows}")
        
        mask_tags = recipes["TAGS"].apply(lambda x: len(x) > 0)
        self.logger.info(f"🔎 Filter [TAGS > 0]: {mask_tags.sum()} / {total_rows}")
        
        mask_nutrition = recipes["NUTRITION"].apply(lambda x: len(x) == 7)
        self.logger.info(f"🔎 Filter [NUTRITION == 7]: {mask_nutrition.sum()} / {total_rows}")
        
        mask_desc = recipes["DESCRIPTION"].notna()
        self.logger.info(f"🔎 Filter [DESCRIPTION valid]: {mask_desc.sum()} / {total_rows}")
        
        mask_steps = recipes["STEPS"].apply(lambda x: len(x) > 0)
        self.logger.info(f"🔎 Filter [STEPS > 0]: {mask_steps.sum()} / {total_rows}")
        
        mask_ingredients = recipes["INGREDIENTS"].apply(lambda x:  len(x) > 0)
        self.logger.info(f"🔎 Filter [INGREDIENTS > 0]: {mask_ingredients.sum()} / {total_rows}")

        # Combinaison finale
        clean_data = recipes[
            mask_name &
            mask_minutes &
            mask_id &
            mask_submitted &
            mask_tags &
            mask_nutrition &
            mask_desc &
            mask_steps &
            mask_ingredients
        ].copy()
        
        self.logger.info(f"📊 [FINAL] Rows remaining after ALL filters: {len(clean_data)}")

        if len(clean_data) == 0:
            self.logger.error("❌ No rows remain after filtering. Aborting.")
            return

        clean_data["FILTERS"] = clean_data["TAGS"].apply(lambda x: [])

        # ==================================================================================
        # 4. SAMPLING & SCHEMA
        # ==================================================================================
        self.logger.info("--- [STEP 4] Sampling & Schema ---")

        columns_spec = {
            "NAME": "VARCHAR(16777216)",
            "ID": "NUMBER(38,0)",
            "MINUTES": "NUMBER(38,0)",
            "CONTRIBUTOR_ID": "NUMBER(38,0)",
            "SUBMITTED": "DATE",
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
            "SERVING_SIZE": "VARCHAR(16777216)",
            "SERVINGS": "NUMBER(38,0)",
            "SEARCH_TERMS": "ARRAY",
            "FILTERS": "ARRAY"
        }

        sample_size_50k = min(50000, len(clean_data))
        clean_data_50k = clean_data.sample(n=sample_size_50k, random_state=42).reset_index(drop=True)
        
        sample_size_1k = min(1000, len(clean_data_50k))
        dev_data_1k = clean_data_50k.sample(n=sample_size_1k, random_state=42).reset_index(drop=True)

        cols_to_keep = [c for c in columns_spec.keys() if c in clean_data_50k.columns]
        clean_data_50k = clean_data_50k[cols_to_keep]
        dev_data_1k = dev_data_1k[cols_to_keep]

        # ==================================================================================
        # 5. WRITING
        # ==================================================================================
        
        self.logger.info(f"Writing {len(clean_data_50k)} rows to CLEANED...")
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(clean_data_50k, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["cleaned_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        self.logger.info(f"Writing {len(dev_data_1k)} rows to DEV_SAMPLE...")
        self.connector.ensure_table(SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], columns_spec)
        self.connector.write_pandas(dev_data_1k, SNOWFLAKE_CONFIG["database"], SNOWFLAKE_CONFIG["dev_schema"], SNOWFLAKE_CONFIG["cleaned_table"], overwrite=True)

        self.logger.info("✅ Ingestion Finished Successfully.")