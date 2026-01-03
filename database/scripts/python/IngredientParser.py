"""
IngredientParser module for processing and parsing recipe ingredients.

This module handles the parsing, cleaning, and unit conversion of ingredient
quantities from raw recipe data.
"""

import pandas as pd
import numpy as np
import re
import math
from config import OUTPUT_FILES, SNOWFLAKE_CONFIG


class IngredientParser:
    """Parser for recipe ingredients with unit conversion and normalization."""
    
    VULGAR_TO_ASCII = {
        '¼':'1/4','½':'1/2','¾':'3/4','⅐':'1/7','⅑':'1/9','⅒':'1/10',
        '⅓':'1/3','⅔':'2/3','⅕':'1/5','⅖':'2/5','⅗':'3/5','⅘':'4/5',
        '⅙':'1/6','⅚':'5/6','⅛':'1/8','⅜':'3/8','⅝':'5/8','⅞':'7/8'
    }
    
    CONV_VOLUME = {
        'teaspoon': 4.93, 'tsp': 4.93, 
        'tablespoon': 14.79, 'tbsp': 14.79, 
        'cup': 236.5882365,
        'pint': 473.176473, 
        'quart': 946.352946, 
        'gallon': 3785.41, 
        'fluid ounce': 29.5735,
        'dash': 0.625, 
        'splash': 5.91, 
        'pony': 29.57, 
        'jigger': 44.36, 
        'shot': 44.36,
        'snit': 88.72, 
        'wineglass': 118.29, 
        'split': 177.44, 
        'gill': 118.29411825,
        'fluid scruple': 1.1838776, 
        'drop': 0.05, 
        'smidgen': 0.15, 
        'pinch': 0.7399235026,
        'scoop': 56
    }
    
    CONV_WEIGHT = {
        'teaspoon': 4.93, 'tsp': 4.93, 
        'tablespoon': 14.79, 'tbsp': 14.79, 
        'cup': 236.5882365,
        'pint': 473.176473, 
        'quart': 946.352946, 
        'gallon': 3785.41, 
        'fluid ounce': 29.5735,
        'dash': 0.625, 
        'splash': 5.91, 
        'pony': 29.57, 
        'jigger': 44.36, 
        'shot': 44.36,
        'snit': 88.72, 
        'wineglass': 118.29, 
        'split': 177.44, 
        'gill': 118.29411825,
        'fluid scruple': 1.1838776, 
        'drop': 0.05, 
        'smidgen': 0.15, 
        'pinch': 0.7399235026,
        'scoop': 56,
        'ounce': 28.3495, 'oz': 28.3495, 
        'pound': 453.59237, 'lb': 453.59237
    }
    
    def normalize_fractions(self, s: str) -> str:
        """Convert vulgar fraction characters to ASCII equivalents."""
        if not isinstance(s, str):
            return s
        for k, v in self.VULGAR_TO_ASCII.items():
            s = s.replace(k, v)
        return s.replace('⁄', '/')
    
    def parse_single_expr(self, expr: str) -> None | int | float:
        """Parse a single numeric expression (integer, fraction, or decimal)."""
        if not isinstance(expr, str):
            return None
        expr = expr.strip()
        if expr == "":
            return None
        m = re.match(r'^(-?\d+)\s+(\d+)/(\d+)$', expr)
        if m:
            return int(m.group(1)) + int(m.group(2))/int(m.group(3))
        m = re.match(r'^(-?\d+)/(\d+)$', expr)
        if m:
            return int(m.group(1))/int(m.group(2))
        m = re.match(r'^-?\d+(?:[.,]\d+)?$', expr)
        if m:
            return float(expr.replace(',', '.'))
        return None
    
    def parse_quantity_string(self, s: str | None | float) -> float:
        """Parse a quantity string that may contain ranges or multiple parts."""
        if s is None or (isinstance(s, float) and math.isnan(s)) or s == '':
            return None
        s = self.normalize_fractions(str(s))
        s = s.replace('–', '-').replace('—', '-')
        s = re.sub(r'\s*-\s*', ' - ', s)
        parts = [p.strip() for p in s.split(' - ') if p.strip()]
        
        vals = [self.parse_single_expr(p) for p in parts[:2]]
        for i, v in enumerate(vals):
            if v is None:
                m = re.search(r'(?:(\d+)\s+(\d+/\d+))|(\d+/\d+)|(-?\d+(?:[.,]\d+)?)', parts[i])
                if m:
                    vals[i] = self.parse_single_expr(m.group(0))
        parsed_vals = [v for v in vals if v is not None]
        if not parsed_vals:
            return None
        return sum(parsed_vals)/len(parsed_vals)
    
    def clean_list_column(self, col: pd.Series) -> pd.Series:
        """Clean list columns from string representation to actual lists."""
        def _clean(l):
            if l is None or isinstance(l, list):
                return l
            return [s.strip() for s in l.replace('[', '').replace(']', '').replace("'", '').split(",")]
        return col.apply(_clean)
    
    def normalize_units(self, col: pd.Series) -> pd.Series:
        """Normalize unit names (singular forms, lowercase)."""
        all_units = set(self.CONV_VOLUME.keys()) | set(self.CONV_WEIGHT.keys())
        units = {u for u in all_units if len(u.split()) == 1}
        
        plural_to_singular = {u+'s': u for u in units}
        plural_to_singular.update({
            'lbs': 'lb',
            'fluid ounces': 'fluid ounce',
            'gills': 'gill',
            'tbsp': 'tablespoon',
            'tsps': 'teaspoon',
            'ozs': 'ounce'
        })
        
        col_norm = col.str.strip().str.lower().replace(plural_to_singular, regex=False)
        return col_norm
    
    def convert_units_vectorized(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert quantities to standard units (ml for volume, g for weight)."""
        unit_norm = df['unit'].astype(str).str.strip().str.lower()
        
        df['qty_ml'] = np.nan
        df['qty_g'] = np.nan
        
        mask_vol = unit_norm.isin(self.CONV_VOLUME.keys())
        df.loc[mask_vol, 'qty_ml'] = (
            df.loc[mask_vol, 'quantity'].astype(float) *
            unit_norm[mask_vol].map(self.CONV_VOLUME).astype(float)
        )
        
        mask_wt = unit_norm.isin(self.CONV_WEIGHT.keys())
        df.loc[mask_wt, 'qty_g'] = (
            df.loc[mask_wt, 'quantity'].astype(float) *
            unit_norm[mask_wt].map(self.CONV_WEIGHT).astype(float)
        )
        
        return df
    
    def replace_qty_for_ingredients(self, df: pd.DataFrame, ingredients_list: list, 
                                   default_value: float) -> pd.DataFrame:
        """Replace quantities for specific ingredients with default values."""
        ingredients_list_clean = [ing.strip().lower() for ing in ingredients_list]
        ing_clean = df['ingredients'].astype(str).str.strip().str.lower()
        
        mask = ing_clean.isin(ingredients_list_clean)
        
        df.loc[mask, 'qty_g'] = np.where(
            df.loc[mask, 'quantity'].isna(),
            default_value,
            default_value * df.loc[mask, 'quantity']
        )
        df.loc[mask, 'qty_ml'] = np.where(df.loc[mask, 'unit'].isna(), np.nan, df.loc[mask, 'qty_ml'])
        df.loc[mask, 'unit'] = 'g'
        return df
    
    def process_ingredients_with_enrich(self, raw_csv_path: str, enrich_csv_path: str, 
                                        output_csv_path: str) -> pd.DataFrame:
        """
        Process ingredients with enriched data and unit conversions.
        
        Args:
            raw_csv_path: Path to raw recipes CSV
            enrich_csv_path: Path to enriched recipes CSV
            output_csv_path: Path to output CSV file
            
        Returns:
            Processed DataFrame with standardized quantities
        """
        df_raw = pd.read_csv(raw_csv_path, index_col='id')
        
        df_enrich = pd.read_csv(enrich_csv_path, index_col='id')
        df_enrich = df_enrich[['ingredients', 'quantities']]
        
        df = df_raw.drop(columns=['ingredients'], errors='ignore').join(df_enrich, how='inner')
        
        df.replace({'[]': None, '': None}, inplace=True)
        
        df_ing = df[['ingredients', 'quantities']].copy()
        df_ing['ingredients'] = self.clean_list_column(df_ing['ingredients'])
        df_ing['quantities'] = self.clean_list_column(df_ing['quantities'])
        df_ing = df_ing[df_ing['ingredients'].str.len() == df_ing['quantities'].str.len()]
        df_ing = df_ing.explode(['ingredients', 'quantities'])
        df_ing.rename(columns={'quantities': 'quantity_raw_str'}, inplace=True)
        
        df_ing['unit'] = df_ing['quantity_raw_str'].str.extract(
            r'([A-Za-z]+(?:\s[A-Za-z]+)?)', expand=False
        ).fillna('').str.lower().str.strip()
        df_ing['unit'] = self.normalize_units(df_ing['unit'])
        
        df_ing['quantity'] = df_ing['quantity_raw_str'].str.replace(
            r'([A-Za-z]+(?:\s[A-Za-z]+)?)', '', regex=True
        )
        df_ing['quantity'] = df_ing['quantity'].apply(
            lambda x: round(self.parse_quantity_string(x), 3) 
            if self.parse_quantity_string(x) is not None else np.nan
        )
        
        df_ing.replace({'': np.nan}, inplace=True)
        
        df_ing = self.convert_units_vectorized(df_ing)
        
        # Replace quantities for specific ingredients with standard defaults
        df_ing = self.replace_qty_for_ingredients(
            df_ing,
            ['cinamon', 'garlic powder', 'salt', 'kosher salt', 'sea salt', 'pepper',
             'white pepper', 'ground pepper', 'fresh ground pepper', 'ground black pepper',
             'fresh ground black pepper', 'black pepper', 'cracked black pepper',
             'salt and pepper', 'salt and black pepper', 'salt & pepper',
             'salt and fresh pepper', 'salt & freshly ground black pepper', 'sugar',
             'powdered sugar'],
            4.93
        )
        df_ing = self.replace_qty_for_ingredients(
            df_ing,
            ['honey', 'oil', 'vegetable oil', 'olive oil', 'extra virgin olive oil',
             'butter', 'tomato paste'],
            14.79
        )
        df_ing = self.replace_qty_for_ingredients(df_ing, ['egg', 'eggs'], 60)
        df_ing = self.replace_qty_for_ingredients(
            df_ing,
            ['onions', 'onion', 'red onions', 'yellow onions', 'parmesan cheese', 'cheese'],
            100
        )
        
        mask_unit_nan = df_ing['unit'].isna()
        df_ing.loc[mask_unit_nan & df_ing['qty_g'].isna(), 'qty_ml'] = np.nan
        
        df_ing.to_csv(output_csv_path)
        return df_ing
    
    def main(self, raw_csv_path: str = f"./dataset/{OUTPUT_FILES['raw_recipes']}",
             enrich_csv_path: str = f"./dataset/{OUTPUT_FILES['recipes_images']}",
             output_csv_path: str = f"./dataset/{OUTPUT_FILES['ingredients_parsing']}") -> pd.DataFrame:
        """
        Main entry point for ingredient parsing.
        
        Args:
            raw_csv_path: Path to raw recipes CSV
            enrich_csv_path: Path to enriched recipes CSV
            output_csv_path: Path to output CSV file
            
        Returns:
            Processed DataFrame
        """
        return self.process_ingredients_with_enrich(raw_csv_path, enrich_csv_path, output_csv_path)


if __name__ == "__main__":
    parser = IngredientParser()
    df_final = parser.main()
