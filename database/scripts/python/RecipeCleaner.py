import ast
import logging
import os
from typing import List

import pandas as pd

from config import CACHE_DIR, GOOGLE_DRIVE_FILES, KAGGLE_DATASETS, OUTPUT_FILES
from DataLoader import DataLoader


class RecipeCleaner:
    """Handles recipe data cleaning and validation."""

    def __init__(self, data_loader: DataLoader):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_loader = data_loader

    def safe_parse_list(self, list_str: str) -> List:
        """Safely parse a string representation of a list."""
        try:
            parsed = ast.literal_eval(list_str)
            if isinstance(parsed, list):
                return parsed
            return []
        except (ValueError, SyntaxError, TypeError):
            return []

    def check_consistency(self, row) -> List[str]:
        """Check data consistency for a recipe row."""
        errors = []

        steps_list = self.safe_parse_list(row.get('steps', '[]'))
        ingredients_list = self.safe_parse_list(row.get('ingredients', '[]'))

        # Check n_steps consistency
        try:
            n_steps = int(row.get('n_steps', 0))
        except Exception:
            n_steps = None

        if n_steps is not None and len(steps_list) != n_steps:
            errors.append(
                f"Inconsistent Steps: n_steps={n_steps} but {len(steps_list)} steps found."
            )

        # Check n_ingredients consistency
        try:
            n_ingredients = int(row.get('n_ingredients', 0))
        except Exception:
            n_ingredients = None

        if n_ingredients is not None and len(ingredients_list) != n_ingredients:
            errors.append(
                f"Inconsistent Ingredients: n_ingredients={n_ingredients} but {len(ingredients_list)} ingredients found."
            )

        # Business logic: preparation time
        try:
            minutes = float(row.get('minutes', 0))
        except Exception:
            minutes = None

        if minutes is not None and minutes < 0:
            errors.append(f"Invalid time: negative minutes ({row.get('minutes')})")

        # Required fields
        name = row.get('name')
        if pd.isna(name) or str(name).strip() == "":
            errors.append("Missing recipe name")

        return errors

    def run_transformation(self, consistency_check: bool = False) -> pd.DataFrame:
        """Run the complete data transformation pipeline."""
        # Ensure data cache exists
        os.makedirs(CACHE_DIR, exist_ok=True)

        # Download from Drive
        raw_recipes_path = self.data_loader.load_from_drive(
            GOOGLE_DRIVE_FILES["raw_recipes"], OUTPUT_FILES["raw_recipes"]
        )
        self.data_loader.load_from_drive(
            GOOGLE_DRIVE_FILES["raw_interactions"], OUTPUT_FILES["raw_interactions"]
        )
        self.data_loader.load_from_drive(
            GOOGLE_DRIVE_FILES["cleaned_ingredients"], OUTPUT_FILES["cleaned_ingredients"]
        )

        # Download from Kaggle
        recipes_images_path = self.data_loader.load_from_kaggle(
            KAGGLE_DATASETS["recipes_images"], OUTPUT_FILES["recipes_images"]
        )
        recipes_w_search_terms_path = self.data_loader.load_from_kaggle(
            KAGGLE_DATASETS["recipes_w_search_terms"], OUTPUT_FILES["recipes_w_search_terms"]
        )

        # Read main dataframes
        self.logger.info(f"Reading raw recipes from: {raw_recipes_path}")
        raw_recipes_df = pd.read_csv(raw_recipes_path)

        df_img = pd.read_csv(recipes_images_path)[["id", "has_image", 'image_url']]
        df_quantity = pd.read_csv(recipes_w_search_terms_path)[["id", "ingredients_raw_str", "serving_size", 'servings', 'search_terms']]

        df_quantity["serving_size"] = df_quantity["serving_size"].astype(str).apply(lambda x: x[3:-3] if len(x) > 6 else x)
        df_quantity["search_terms"] = df_quantity.search_terms.astype(str).apply(lambda x: x.replace("{", "[").replace("}", "]"))

        res = raw_recipes_df.merge(df_img, how="inner", on="id")
        res = res.merge(df_quantity, how="inner", on="id")

        # Data quality checks
        self.logger.info(f"Analyzing {len(res)} rows of data...")
        res['validation_errors'] = res.apply(self.check_consistency, axis=1)

        invalid_rows = res[res['validation_errors'].map(len) > 0]
        if consistency_check:
            if invalid_rows.empty:
                self.logger.info("No consistency errors detected!")
            else:
                self.logger.warning(f"{len(invalid_rows)} recipes have quality issues.")
                for index, row in invalid_rows.iterrows():
                    recette_id = row['id']
                    nom = row['name']
                    erreurs = row['validation_errors']
                    self.logger.warning(f"Recipe ID {recette_id} ('{nom}'): {erreurs}")

        # Export a sample to CSV for Snowflake loading
        df_sample = res.iloc[0:110000]
        out_path = os.path.join(CACHE_DIR, OUTPUT_FILES["cleaned_recipes"])
        df_sample.to_csv(out_path, index=False, sep=",")
        self.logger.info(f"Sample exported to: {out_path}")

        return res


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = DataLoader()
    cleaner = RecipeCleaner(loader)
    cleaner.run_transformation()
