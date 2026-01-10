"""
Data transformation module for NutriRAG.

Provides the DataTransformer class for cleaning and validating recipe data.
"""

import ast
import logging
from typing import List

import pandas as pd


class DataTransformer:
    """Handles recipe data cleaning and validation."""

    def __init__(self):
        """Initialize DataTransformer."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def safe_parse_list(self, list_str: str) -> List:
        """
        Safely parse a string representation of a list.

        Args:
            list_str: String to parse

        Returns:
            List object, or empty list if parsing fails
        """
        try:
            parsed = ast.literal_eval(list_str)
            if isinstance(parsed, list):
                return parsed
            return []
        except (ValueError, SyntaxError, TypeError):
            return []

    def check_consistency(self, row) -> List[str]:
        """
        Check data consistency for a recipe row.

        Args:
            row: Pandas Series representing a recipe row

        Returns:
            List of error messages, empty if no errors found
        """
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
                f"Inconsistent Steps: n_steps={n_steps} but {len(steps_list)} steps found"
            )

        # Check n_ingredients consistency
        try:
            n_ingredients = int(row.get('n_ingredients', 0))
        except Exception:
            n_ingredients = None

        if n_ingredients is not None and len(ingredients_list) != n_ingredients:
            errors.append(
                f"Inconsistent Ingredients: n_ingredients={n_ingredients} but {len(ingredients_list)} found"
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

    def transform(
        self,
        raw_recipes_df: pd.DataFrame,
        consistency_check: bool = False
    ) -> pd.DataFrame:
        """
        Transform and validate recipe data.

        Args:
            raw_recipes_df: Raw recipes DataFrame
            consistency_check: Whether to perform consistency checks

        Returns:
            Transformed DataFrame
        """
        self.logger.info(f"Transforming {len(raw_recipes_df)} rows of data...")

        # Data quality checks
        raw_recipes_df['validation_errors'] = raw_recipes_df.apply(
            self.check_consistency,
            axis=1
        )

        invalid_rows = raw_recipes_df[raw_recipes_df['validation_errors'].map(len) > 0]

        if consistency_check:
            if invalid_rows.empty:
                self.logger.info("✅ No consistency errors detected!")
            else:
                self.logger.warning(f"⚠️ {len(invalid_rows)} recipes have quality issues")
                for index, row in invalid_rows.iterrows():
                    recipe_id = row.get('id', 'unknown')
                    recipe_name = row.get('name', 'unknown')
                    errors = row.get('validation_errors', [])
                    self.logger.warning(
                        f"Recipe ID {recipe_id} ('{recipe_name}'): {errors}"
                    )

        return raw_recipes_df
