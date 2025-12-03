import ast
import os
from typing import List
import pandas as pd

from load_data import load_from_drive, load_from_kaggle


def safe_parse_list(list_str: str) -> List:
    try:
        parsed = ast.literal_eval(list_str)
        if isinstance(parsed, list):
            return parsed
        return []
    except (ValueError, SyntaxError, TypeError):
        return []

def check_consistency(row) -> List[str]:
    errors = []

    steps_list = safe_parse_list(row.get('steps', '[]'))
    ingredients_list = safe_parse_list(row.get('ingredients', '[]'))

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

def run_transformation(consistency=False):
    # Ensure data cache exists
    os.makedirs("./data_cache", exist_ok=True)

    # Drive file IDs and target filenames
    raw_recipes = '1fxvf7ghbgH0xkvHkPFM_K8_JbeL9QX3L'
    raw_interactions = '10zdNLf2oKiMY30ZacdwdF1AEpkrbyoUN'
    cleaned_ingredients = '1HjT5RiZnxlg2PkcMLlqzxBjeeRGITYvx'

    # Download from Drive (these functions download into ./data_cache)
    raw_recipes_path = load_from_drive(raw_recipes,"RAW_recipes.csv")
    raw_interactions_path = load_from_drive(raw_interactions,"RAW_INTERACTIONS.csv")
    cleaned_ingredients_path = load_from_drive(cleaned_ingredients,"CLEANED_INGREDIENTS.csv")

    # Kaggle datasets (this will place files into ./data_cache)
    recipes_images = 'behnamrahdari/foodcom-enhanced-recipes-with-images'
    recipes_w_search_terms = 'shuyangli94/foodcom-recipes-with-search-terms-and-tags'

    # Trigger downloads (depending on implementation, these may be no-ops if files already exist)
    recipes_images_path = load_from_kaggle(recipes_images,"recipes_enhanced_v2.csv")
    recipes_w_search_terms_path = load_from_kaggle(recipes_w_search_terms,"recipes_w_search_terms.csv")
        
    # Read main dataframes
    print(f"Reading raw recipes from: {raw_recipes_path}")
    raw_recipes_df = pd.read_csv(raw_recipes_path)

    df_img = pd.read_csv(recipes_images_path)[["id", "has_image", 'image_url']]
    df_quantity = pd.read_csv(recipes_w_search_terms_path)[["id", "ingredients_raw_str", "serving_size", 'servings', 'search_terms']]

    df_quantity["serving_size"] = df_quantity["serving_size"].astype(str).apply(lambda x: x[3:-3] if len(x) > 6 else x)
    df_quantity["search_terms"] = df_quantity.search_terms.astype(str).apply(lambda x: x.replace("{", "[").replace("}", "]"))

    res = raw_recipes_df.merge(df_img, how="inner", on="id")
    res = res.merge(df_quantity, how="inner", on="id")

    # Data quality checks
    print(f"Analyzing {len(res)} rows of data...\n")
    res['validation_errors'] = res.apply(check_consistency, axis=1)

    invalid_rows = res[res['validation_errors'].map(len) > 0]
    if consistency:
        if invalid_rows.empty:
            print("✅ No consistency errors detected!")
        else:
            print(f"❌ {len(invalid_rows)} recipes have quality issues:\n")
            for index, row in invalid_rows.iterrows():
                recette_id = row['id']
                nom = row['name']
                erreurs = row['validation_errors']
                print(f"Recipe ID {recette_id} ('{nom}'):")
                for err in erreurs:
                    print(f"  - {err}")
                print("-" * 40)

    # Export a sample to CSV for Snowflake loading
    df_sample = res.iloc[0:110000]
    out_path = os.path.join(".", "data_cache", "clean_recipes_to_snowflake.csv")
    df_sample.to_csv(out_path, index=False, sep=",")
    print(f"Sample exported to: {out_path}")


if __name__ == "__main__":
    run_transformation()
