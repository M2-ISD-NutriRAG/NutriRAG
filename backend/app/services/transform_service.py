import traceback
import pandas as pd
import numpy as np
import threading
import logging
from typing import Dict, List, Any, Optional, Tuple

from snowflake.snowpark.functions import col, lower, trim, row_number
from snowflake.snowpark.window import Window
from snowflake.snowpark import Session

from app.models.transform import (
    TransformConstraints,
    TransformResponse,
    NutritionDelta,
    TransformationType,
    Recipe,
)
from math import ceil
from app.udf.transform_recipe import (
    parse_query_result,
)  # Specific to python only usage

NUTRIENT_BASIS_GRAMS = 100
NUTRITION_COLS = [
    "ENERGY_KCAL", "PROTEIN_G", "FAT_G", "SATURATED_FATS_G", "CARB_G",
    "FIBER_G", "SUGAR_G", "SODIUM_MG", "CALCIUM_MG", "IRON_MG",
    "MAGNESIUM_MG", "POTASSIUM_MG", "VITC_MG"
]

class TransformService:
    _pca_data_cache = None
    _pca_lock = threading.Lock()
    # check if async necessary for the constructor
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.ingredients_cache: Dict[str, Optional[Dict]] = {}
        self.recipe_qty_cache: Dict[str, List[Tuple[str, Optional[float]]]] = {}
        self.recipe_nutrition_cache: Dict[str, Dict[str, Optional[Dict[str, Any]]]] = {}
        self.pca_data = None  # ingredient coordinates for clustering 
        self.load_pca_data()

    def fetch_recipe_quantities(self, recipe_id: str) -> Dict[str, Optional[float]]:
            """
            Returns list of (ingredient_string, qty_g_or_none) from INGREDIENTS_QUANTITY.
            Cached per recipe.
            """
            if recipe_id in self.recipe_qty_cache:
                return self.recipe_qty_cache[recipe_id]
            
            sdf = (
            self.session.table("NUTRIRAG_PROJECT.RAW.INGREDIENTS_QUANTITY")
            .filter(col("ID") == recipe_id)
            .select(col("INGREDIENTS"), col("QTY_G"))
            )

            rows = sdf.collect()  # <-- materialize results
            out: Dict[str, Optional[float]] = {}

            for r in rows:
                ing = r["INGREDIENTS"]
                qty = r["QTY_G"]
                if ing is None:
                    continue
                out[ing] = float(qty) if qty is not None else None

            self.recipe_qty_cache[recipe_id] = out
            return out

    def fetch_ingredients_nutrition(self, recipe_id: str, ingredients: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
         Returns mapping:
          key = LOWER(TRIM(ingredient_from_recipe_name))
          val = dict of nutrition columns per 100g (or None if not found)
        Cached per recipe+ingredient key.
        """
        if recipe_id not in self.recipe_nutrition_cache:
            self.recipe_nutrition_cache[recipe_id] = {}

        keys = [(s or "").strip().lower() for s in ingredients]
        keys = [k for k in keys if k]
        unique_keys = sorted(set(keys))

        missing = [k for k in unique_keys if k not in self.recipe_nutrition_cache[recipe_id]]
        if not missing:
            return self.recipe_nutrition_cache[recipe_id]

        # Default missing keys to None so we don't re-query forever
        for k in missing:
            self.recipe_nutrition_cache[recipe_id][k] = None

        im = self.session.table("NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING")
        ci = self.session.table("NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS")

        ing_key_expr = lower(trim(col("INGREDIENT_FROM_RECIPE_NAME")))

        joined = (
            im.filter(col("RECIPE_ID") == recipe_id)
              .with_column("ING_KEY", ing_key_expr)
              .filter(col("ING_KEY").isin(missing))
              .join(ci, col("INGREDIENT_ID") == col("NDB_NO"), how="left")
              .select(
                  col("ING_KEY"),
                  col("ENERGY_KCAL"),
                  col("PROTEIN_G"),
                  col("FAT_G"),
                  col("SATURATED_FATS_G"),
                  col("CARB_G"),
                  col("FIBER_G"),
                  col("SUGAR_G"),
                  col("SODIUM_MG"),
                  col("CALCIUM_MG"),
                  col("IRON_MG"),
                  col("MAGNESIUM_MG"),
                  col("POTASSIUM_MG"),
                  col("VITC_MG"),
                  col("SCORE_SANTE"),
              )
        )

        w = Window.partition_by(col("ING_KEY")).order_by(col("SCORE_SANTE").desc_nulls_last())
        ranked = joined.with_column("RN", row_number().over(w)).filter(col("RN") == 1)

        rows = ranked.select(
            "ING_KEY",
            "ENERGY_KCAL",
            "PROTEIN_G",
            "FAT_G",
            "SATURATED_FATS_G",
            "CARB_G",
            "FIBER_G",
            "SUGAR_G",
            "SODIUM_MG",
            "CALCIUM_MG",
            "IRON_MG",
            "MAGNESIUM_MG",
            "POTASSIUM_MG",
            "VITC_MG",
        ).collect()

        for r in rows:
            ing_key = r["ING_KEY"]
            vals = [r[c] for c in NUTRITION_COLS]
            self.recipe_nutrition_cache[recipe_id][ing_key] = dict(zip(NUTRITION_COLS, vals))

        return self.recipe_nutrition_cache[recipe_id]

    def compute_recipe_nutrition_totals(
        self,
        recipe_id: str,
        ingredients: List[str],
        serving_size: float,
        servings: float,
    ) -> NutritionDelta:
        """
        Compute recipe nutrition information for all ingredients
        Returns:
        NutritionDelta
            Total nutrients for the  recipe
        """
        total_weight = (serving_size or 0.0) * (servings or 0.0)
        ingredients_quantity = self.fetch_recipe_quantities(recipe_id)
        ingredients_nutrition = self.fetch_ingredients_nutrition(recipe_id, ingredients)
        
        known_weight = 0.0
        unknown_count = 0

        for _, qty in ingredients_quantity.items():
            if qty is None:
                unknown_count += 1
            else:
                known_weight += float(qty)

        if unknown_count > 0:
            fill_qty = max(total_weight - known_weight, 0.0) / unknown_count * 0.5 # 0.5 to follow group 1 logic appended to db
        else:
            fill_qty = 0.0
        
        recipe_nutrition = NutritionDelta(
            calories=0.0,
            protein_g=0.0,
            fat_g=0.0,
            saturated_fats_g=0.0,
            carb_g=0.0,
            fiber_g=0.0,
            sugar_g=0.0,
            sodium_mg=0.0,
            calcium_mg=0.0,
            iron_mg=0.0,
            magnesium_mg=0.0,
            potassium_mg=0.0,
            vitamin_c_mg=0.0,
            health_score=0.0
        )
        for name, nutrition in ingredients_nutrition.items():
            if nutrition is None:
                continue
            quantity = ingredients_quantity.get(name)
            if quantity is None:
                quantity = fill_qty
            factor = float(quantity) / NUTRIENT_BASIS_GRAMS

            recipe_nutrition.calories += nutrition.calories["ENERGY_KCAL"] * factor
            recipe_nutrition.protein_g += nutrition["PROTEIN_G"] * factor
            recipe_nutrition.fat_g += nutrition["FAT_G"] * factor
            recipe_nutrition.saturated_fats_g += nutrition["SATURATED_FATS_G"] * factor
            recipe_nutrition.carb_g += nutrition["CARB_G"] * factor
            recipe_nutrition.fiber_g += nutrition["FIBER_G"] * factor
            recipe_nutrition.sugar_g += nutrition["SUGAR_G"] * factor
            recipe_nutrition.sodium_mg += nutrition["SODIUM_MG"] * factor

            recipe_nutrition.calcium_mg += nutrition["CALCIUM_MG"] * factor
            recipe_nutrition.iron_mg += nutrition["IRON_MG"] * factor
            recipe_nutrition.magnesium_mg += nutrition["MAGNESIUM_MG"] * factor
            recipe_nutrition.potassium_mg += nutrition["POTASSIUM_MG"] * factor
            recipe_nutrition.vitamin_c_mg += nutrition["VITAMIN_C_MG"] * factor

        return recipe_nutrition
    
    def scale_nutrition(self, n: NutritionDelta, factor: float) -> NutritionDelta:
        """
        Scales nutrition value for 100g = a portion of the recipe, to represent the score per portion
        Separate from total nutrition calculation to send totals for full recipe if asked 
        """
        return NutritionDelta(
        calories=n.calories * factor,
        protein_g=n.protein_g * factor,
        fat_g=n.fat_g * factor,
        saturated_fats_g=n.saturated_fats_g * factor,
        carb_g=n.carb_g * factor,
        fiber_g=n.fiber_g * factor,
        sugar_g=n.sugar_g * factor,
        sodium_mg=n.sodium_mg * factor,
        calcium_mg=n.calcium_mg * factor,
        iron_mg=n.iron_mg * factor,
        magnesium_mg=n.magnesium_mg * factor,
        potassium_mg=n.potassium_mg * factor,
        vitamin_c_mg=n.vitamin_c_mg * factor,
    )

    def compute_benefit_score(self, protein_g: float, fiber_g: float) -> float:
        """
        Compute the benefit score of a recipe based on total protein and fiber.
        Returns a value in [0, 1].
        """
        protein_ref = 50.0  
        fiber_ref   = 30.0

        s_protein = min(protein_g / protein_ref, 1.0)
        s_fiber   = min((fiber_g or 0.0) / fiber_ref, 1.0)

        benefit_score = (s_protein + s_fiber) / 2.0

        return benefit_score

    def compute_risk_score(
        self,
        sugar_g: float,
        saturated_fats_g: float,
        sodium_mg: float,
        alpha_sugar: float = 1.2,
        alpha_satfat: float = 1.0,
        alpha_sodium: float = 1.5,
    ) -> float:
        """
        Compute risk score where exceeding nutrient limits creates negative scores proportional to how badly limits are exceeded.
        Returns float between -inf and 1.0
        """

        sugar_limit = 50.0     
        satfat_limit = 20.0   
        sodium_limit = 2000.0

        def subscore(x, L, alpha):
            x = max(x, 0.0)
            if x <= L:
                return 1.0 - (x / L)
            else:
                return -alpha * ((x / L) - 1.0)

        h_sugar   = subscore(sugar_g, sugar_limit, alpha_sugar)
        h_satfat  = subscore(saturated_fats_g, satfat_limit, alpha_satfat)
        h_sodium  = subscore(sodium_mg, sodium_limit, alpha_sodium)

        risk_control_score = (h_sugar + h_satfat + h_sodium) / 3.0
        return risk_control_score

    def compute_micronutrient_density_score(
        self,
        calcium_mg: float,
        iron_mg: float,
        magnesium_mg: float,
        potassium_mg: float,
        vitamin_c_mg: float,
    ) -> float:
        """
        Compute a micronutrient density score in [0, 1] based on totals for the recipe.
        """

        calcium_ref   = 1000.0
        iron_ref      = 18.0
        magnesium_ref = 350.0
        potassium_ref = 3500.0
        vitamin_c_ref = 90.0

        m_ca = min(max(calcium_mg, 0.0)   / calcium_ref,   1.0)
        m_fe = min(max(iron_mg, 0.0)      / iron_ref,      1.0)
        m_mg = min(max(magnesium_mg, 0.0) / magnesium_ref, 1.0)
        m_k  = min(max(potassium_mg, 0.0) / potassium_ref, 1.0)
        m_c  = min(max(vitamin_c_mg, 0.0) / vitamin_c_ref,      1.0)

        micronutrient_score = (m_ca + m_fe + m_mg + m_k + m_c) / 5.0

        return micronutrient_score

    def compute_rhi(self, nutrition: NutritionDelta) -> float:
        """
        Compute the Recipe Health Index (RHI) on [0, 100] for a whole recipe.
        Uses:
          - benefit score (protein + fiber, vs daily references)
          - risk score (sugar, saturated fat, sodium vs daily limits, with penalties above limits)
          - micronutrient density score (Ca, Fe, Mg, K, Vit C vs daily references)

        RHI = max(0, 0.4 * risk + 0.4 * benefit + 0.2 * micro) * 100
        """

        benefit = self.compute_benefit_score(protein_g=nutrition.protein_g, fiber_g=nutrition.fiber_g)
        risk = self.compute_risk_score(
            sugar_g=nutrition.sugar_g,
            saturated_fats_g=nutrition.saturated_fats_g,
            sodium_mg=nutrition.sodium_mg,
        )
        micro = self.compute_micronutrient_density_score(
            calcium_mg=nutrition.calcium_mg,
            iron_mg=nutrition.iron_mg,
            magnesium_mg=nutrition.magnesium_mg,
            potassium_mg=nutrition.potassium_mg,
            vitamin_c_mg=nutrition.vitamin_c_mg,
        )

        rhi_raw = 0.4 * risk + 0.4 * benefit + 0.2 * micro

        rhi_0_1 = max(0.0, rhi_raw)
        rhi = rhi_0_1 * 100.0

        return rhi

    def ensure_pca_loaded(self):
        if TransformService._pca_data_cache is None:
            with TransformService._pca_lock:
                if TransformService._pca_data_cache is None:
                    TransformService._pca_data_cache = self.load_pca_data_from_snowflake()
        self.pca_data = TransformService._pca_data_cache
    
    def load_pca_data(self):
        """Load PCA data from Snowflake or CSV as fallback"""
        try:
            # Charger le fichier CSV
            # csv_path = "ingredients_with_clusters.csv"
            # df_csv = pd.read_csv(csv_path)
            query = """
            SELECT
                NDB_No,
                Descrip,
                ENERGY_KCAL,
                PROTEIN_G,
                SATURATED_FATS_G,
                FAT_G,CARB_G,
                SODIUM_MG,SUGAR_G,
                PCA_macro_1,
                PCA_macro_2,
                PCA_macro_3,
                PCA_micro_1,
                PCA_micro_2,
                Cluster_macro,
                Cluster_micro
            FROM NUTRIRAG_PROJECT.ENRICHED.INGREDIENTS
            LIMIT 100;
            """
            result_cluster = self.session.sql(query)
            df = pd.DataFrame(parse_query_result(result_cluster))

            for col in list(df.columns[2:-2]):
                df[col] = df[col].apply(float)

            # Adapter les noms de colonnes pour correspondre au format attendu
            self.pca_data = df.rename(
                columns={
                    "NDB_No": "NDB_No",
                    "DESCRIP": "Descrip",
                    "Energy_kcal": "ENERGY_KCAL",
                    "Protein_g": "PROTEIN_G",
                    "Saturated_fats_g": "SATURATED_FATS_G",
                    "Fat_g": "FAT_G",
                    "Carb_g": "CARB_G",
                    "Sodium_mg": "SODIUM_MG",
                    "Sugar_g": "SUGAR_G",
                    "PCA_MACRO_1": "PCA_macro_1",
                    "PCA_MACRO_2": "PCA_macro_2",
                    "PCA_MACRO_3": "PCA_macro_3",
                    "PCA_MICRO_1": "PCA_micro_1",
                    "PCA_MICRO_2": "PCA_micro_2",
                    "Cluster_macro": "Cluster_macro",
                    "Cluster_micro": "Cluster_micro",
                }
            )

            # Ajouter des colonnes de contraintes par défaut (pas disponibles dans le CSV)
            self.pca_data["is_lactose"] = 0
            self.pca_data["is_gluten"] = 0
            self.pca_data["contains_nuts"] = 0
            self.pca_data["is_vegetarian"] = 0
            self.pca_data["is_vegetable"] = 0

            # Logique simple pour définir quelques contraintes basées sur le nom
            for idx, row in self.pca_data.iterrows():
                descrip_lower = str(row["Descrip"]).lower()

                # Détection lactose (produits laitiers)
                if any(
                    word in descrip_lower
                    for word in ["milk", "cheese", "butter", "cream", "yogurt"]
                ):
                    self.pca_data.at[idx, "is_lactose"] = 1

                # Détection gluten (céréales, pain, etc.)
                if any(
                    word in descrip_lower
                    for word in ["wheat", "bread", "flour", "pasta", "cereal"]
                ):
                    self.pca_data.at[idx, "is_gluten"] = 1

                # Détection noix
                if any(
                    word in descrip_lower
                    for word in ["nut", "almond", "peanut", "walnut", "pecan"]
                ):
                    self.pca_data.at[idx, "contains_nuts"] = 1

                # Détection végétarien (pas de viande/poisson)
                if not any(
                    word in descrip_lower
                    for word in [
                        "beef",
                        "pork",
                        "chicken",
                        "fish",
                        "meat",
                        "turkey",
                        "lamb",
                    ]
                ):
                    self.pca_data.at[idx, "is_vegetarian"] = 1

                # Détection végétal (fruits, légumes, etc.)
                if any(
                    word in descrip_lower
                    for word in [
                        "vegetable",
                        "fruit",
                        "bean",
                        "pea",
                        "lentil",
                        "spinach",
                        "carrot",
                        "tomato",
                    ]
                ):
                    self.pca_data.at[idx, "is_vegetable"] = 1

            logging.info("Success: PCA ingredients coordinates successfully loaded.")

        except Exception as e:
            logging.error(f"Failure: PCA ingredients coordinates loading error. Error: {str(e)}. Traceback: {traceback.format_exc()}")
            self.pca_data = None

    def get_neighbors_pca(
        self,
        ingredient_name: str,
        constraints: TransformConstraints = None,
        micro_weight: float = 0.3,
        macro_weight: float = 0.7,
        k: int = 5,
    ) -> Dict:
        """
        Find the k best substitutes for an ingredient using PCA macro/micro
        
        Args:
            ingredient_name: ingredient to substitute
            constraints: transformation constraints
            micro_weight: weight of micronutrients 
            macro_weight: weight of macronutrients
            k: number of substitutes to return
            
        Returns:
            Dict with the best substitutes 
        """
        if self.pca_data is None:
            logging.warning("Failure: PCA ingredients coordinates missing.")
            return None
            
        # Clean ingredient name
        ingredient_clean = ingredient_name.lower().strip()

        # Search for ingredient in PCA Data 
        matching_rows = self.pca_data[
            self.pca_data["Descrip"]
            .str.lower()
            .str.contains(ingredient_clean, na=False)
        ]

        if matching_rows.empty:
            logging.warning(f"Failure:  Ingredient '{ingredient_name}' not found in PCA data")
            return None
            
        # Take the first match
        row = matching_rows.iloc[0]
        logging.info(f"Success: Ingredient found: {ingredient_name} → {row['Descrip']}")
        
        # Copy data for filtering based on constraints
        df_filtered = self.pca_data.copy()

        # Apply constraint filters
        if constraints:
            CONSTRAINT_TO_COLUMN = {
                "no_lactose": ("is_lactose", 0),
                "no_gluten": ("is_gluten", 0),
                "no_nuts": ("contains_nuts", 0),
                "vegetarian": ("is_vegetarian", 1),
                "vegan": ("is_vegetable", 1),
            }

            for constraint_name, (
                col,
                allowed_val,
            ) in CONSTRAINT_TO_COLUMN.items():
                if getattr(constraints, constraint_name, False):
                    # Keep only ingredients that meet the constraint OR the original ingredient
                    if col in df_filtered.columns:
                        df_filtered = df_filtered[
                            (df_filtered[col] == allowed_val)
                            | (
                                df_filtered["Descrip"].str.lower()
                                == ingredient_clean
                            )
                        ]
        
        # PCA columns
        macro_cols = ['PCA_macro_1', 'PCA_macro_2', 'PCA_macro_3']
        micro_cols = ['PCA_micro_1', 'PCA_micro_2']
        
        # Check that columns exist
        available_macro_cols = [col for col in macro_cols if col in df_filtered.columns]
        available_micro_cols = [col for col in micro_cols if col in df_filtered.columns]
        
        if not available_macro_cols and not available_micro_cols:
            logging.warning(f"Failure:  No pca coordinates available in pca dataframe.")
            return None

        macro_vec = (
            row[available_macro_cols].values
            if available_macro_cols
            else np.array([])
        )
        micro_vec = (
            row[available_micro_cols].values
            if available_micro_cols
            else np.array([])
        )

        def euclidean_distance(a, b):
            return np.linalg.norm(a - b) if len(a) > 0 and len(b) > 0 else 0
        
        # Exclude the original ingredient
        df_filtered = df_filtered[df_filtered['Descrip'] != row['Descrip']]
        
        if df_filtered.empty:
            logging.warning("Failure: No substitute found after applying constraints")
            return None
        
        # Calculate global distances (macro + micro combination)
        df_filtered = df_filtered.copy()
        
        # Calculate macro distance
        if available_macro_cols:
            df_filtered["dist_macro"] = df_filtered[available_macro_cols].apply(
                lambda x: euclidean_distance(macro_vec, x.values), axis=1
            )
        else:
            df_filtered['dist_macro'] = 0
        
        # Calculate micro distance  
        if available_micro_cols:
            df_filtered["dist_micro"] = df_filtered[available_micro_cols].apply(
                lambda x: euclidean_distance(micro_vec, x.values), axis=1
            )
        else:
            df_filtered['dist_micro'] = 0
        
        # Combined global score
        df_filtered['global_score'] = (
            macro_weight * df_filtered['dist_macro'] + 
            micro_weight * df_filtered['dist_micro']
        )

        # -------------------------
        # Filter similarities (not regex after all), 30/12/25
        # -------------------------
        main_word = ingredient_clean.split()[0] # only the first word for now

        def filter_similar_df(df, k):
            filtered_rows = []
            for _, row_ in df.iterrows():
                name_lower = row_['Descrip'].lower()
                if not name_lower.startswith(main_word):
                    filtered_rows.append(row_)
                if len(filtered_rows) >= k:
                    break
            return pd.DataFrame(filtered_rows)
        
        # Sort by global score and take the top k
        best_substitutes = df_filtered.nsmallest(k, 'global_score')
        # Filter ingredients with the same base name
        best_substitutes = filter_similar_df(best_substitutes, k)
        
        result = {
            "input_ingredient": row['Descrip'],
            "best_substitutes": []
        }
        
        for _, substitute_row in best_substitutes.iterrows():
            result["best_substitutes"].append(
                {
                    "name": substitute_row["Descrip"],
                    "global_score": substitute_row["global_score"],
                    "macro_distance": substitute_row["dist_macro"],
                    "micro_distance": substitute_row["dist_micro"],
                    "nutrition": {
                        "calories": substitute_row["ENERGY_KCAL"],
                        "protein": substitute_row["PROTEIN_G"],
                        "saturated_fat": substitute_row["SATURATED_FATS_G"],
                        "sodium": substitute_row["SODIUM_MG"],
                        "sugar": substitute_row["SUGAR_G"],
                    },
                }
            )

        return result
    
    def get_health_score(self, new_ingredients: List[str], recipe_id : int, serving_size : float, servings :float) -> NutritionDelta:
        """
        Calculates health score for a recipe based on give ingredients
        """
        new_recipe_nutrition = self.compute_recipe_nutrition_totals(
                recipe_id=recipe_id,
                ingredients=new_ingredients,
                serving_size=serving_size,
                servings=servings
            )
        denom = (serving_size or 0) * (servings or 0)
        if denom > 0:
            scaled_nutrition = self.scale_nutrition(
            new_recipe_nutrition,
            factor=100.0 / denom
            )
        else :
            scaled_nutrition = new_recipe_nutrition ## fallback servings null
        rhi_score = self.compute_rhi(scaled_nutrition)
        new_recipe_nutrition.health_score = rhi_score
        return new_recipe_nutrition
    

    def judge_substitute(self, candidats: List[Dict[str, Any]],recipe_ingredients: List[str], recipe_id: int, serving_size: float, servings: float) -> Tuple[str,NutritionDelta]:
        """
        Final ingredient choice between list of candidats

        Args:
            candidats: list of possible ingredients to substitute with (extracted from get_neighbors_pca() )
            recipe_id, serving_size, servings, recipe_ingredients: recipe information
        Returns:
            ingredient_id
        """
        if not candidats:
            logging.warning("Failure: No candidate found.")
            return None
        best_ing = None
        best_nutrition = NutritionDelta()
        for cand in candidats:
            if best_ing is None:
                best_ing = cand
            else:
                candidat_nutrition = self.get_health_score(recipe_ingredients + [cand["name"]], recipe_id, serving_size, servings)
                best_current_score = self.get_health_score(recipe_ingredients + [best_ing["name"]], recipe_id, serving_size, servings)
                if candidat_nutrition.health_score > best_current_score.health_score:
                    best_ing = cand
                    best_nutrition = candidat_nutrition    
        return best_ing, best_nutrition

    
    def substitute_ingr(self, ingredient: str, contraintes: TransformConstraints, recipe_ingredients: List[str], recipe_id: int, serving_size: float, servings: float) -> Tuple[str, bool, NutritionDelta]:
        """
        Finds a substitute for the given ingredient using PCA in priority
        
        Args:
            ingredient: ingredient to substitute
            contraintes: nutritional constraints
        
        Returns:
            Tuple (substituted_ingredient, substitution_performed)
        """
        result = self.get_neighbors_pca(ingredient, contraintes)

        if not result or not result.get("best_substitutes"):
            return ingredient, False

        candidats = result["best_substitutes"]
        substitute, nutrition = self.judge_substitute(candidats, recipe_ingredients, recipe_id, serving_size, servings)

        if substitute:
            substitute_name = substitute["name"]
            logging.info(f"Success: Found substitute for {ingredient} → {substitute_name} (PCA score: {substitute['global_score']:.3f})")
            return substitute_name, True, nutrition
        
        return ingredient, False, NutritionDelta()

    def _extract_ingredients_from_recipe(self, recipe: Recipe, constraints: TransformConstraints) -> List[str]:
        """
        Use LLM to select the most important ingredient to substitute
        based on full recipe context and constraints.
        """

        base_prompt = f"""
        You are a culinary and nutrition expert.

        You are given a full recipe and a set of dietary and nutritional constraints.

        YOUR TASK:
        - Analyze the recipe as a whole (name, ingredients, quantities, and steps).
        - Identify ONE ingredient that is the most problematic with respect to the constraints.
        - If multiple ingredients violate constraints, select the one that:
        1) Violates the most constraints, OR
        2) Is the most central ingredient in the recipe.
        - If no ingredient should be substituted, answer exactly: NONE.

        IMPORTANT RULES:
        - Answer ONLY with the ingredient name.
        - No explanation.
        - No punctuation.
        - No extra text.

        RECIPE:
        Name: {recipe.name}
        Ingredients: {recipe.ingredients}
        Quantities: {recipe.quantity_ingredients}
        Steps:
        {chr(10).join(recipe.steps)}

        CONSTRAINTS:
        {constraints.__dict__}

        ANSWER:
        """

        try:
            prompt_escaped = base_prompt.replace("'", "''")

            llm_query = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                    '{prompt_escaped}'
                ) AS ingredient_to_substitute
            """
            llm_response = self.session.sql(llm_query).collect()

            parsed_response = parse_query_result(llm_response)
            if not parsed_response:
                return []
            result = str(parsed_response[0]).strip()

            if result.upper() == "NONE":
                return []

            return [result]

        except Exception as e:
            logging.error(
                f"Failure: Error found with ingredient extraction made by LLM. "
                f"Error: {str(e)}. Traceback: {traceback.format_exc()}"
            )
            return []


    def adapt_recipe_with_llm(self, recipe: Recipe, substitutions: Dict) -> str:
        """
        Adapt the recipe steps with substitutions via LLM
        """
        
        # Building the prompt for the LLM
        base_prompt = f"""You are an expert chef specializing in recipe adaptation and ingredient substitution.

        ORIGINAL RECIPE:
        Name: {recipe.name}
        Ingredients: {recipe.ingredients}
        Steps: {recipe.steps}

        SUBSTITUTIONS TO APPLY:
        """

        for original, substitute in substitutions.items():
            base_prompt += f"- Replace '{original}' with '{substitute}'\n"

        base_prompt += """
        YOUR TASK:
        Adapt the recipe steps to incorporate these ingredient substitutions while maintaining the dish's quality and integrity.

        ADAPTATION GUIDELINES:
        1. Modify ONLY the preparation steps that are affected by the substitutions
        2. Preserve the original step numbering and structure
        3. Adjust cooking times if the substitute cooks faster/slower than the original
        4. Adjust temperatures if the substitute requires different heat levels
        5. Note any texture or consistency changes that may occur
        6. Suggest technique modifications if needed (e.g., mixing methods, prep techniques)
        7. Keep instructions clear, concise, and actionable
        8. Maintain the same cooking skill level as the original recipe

        IMPORTANT CONSIDERATIONS:
        - If a substitution significantly impacts flavor, briefly note it in the step
        - If multiple steps use the same ingredient, ensure consistency across all adaptations
        - Do not add new steps; only modify existing ones
        - Do not change unaffected steps

        OUTPUT FORMAT:
        Provide only the adapted recipe steps in numbered format.

        ADAPTED RECIPE STEPS:"""

        try:
            # Échapper les guillemets simples pour éviter les erreurs SQL
            prompt_escaped = base_prompt.replace("'", "''")

            # Construire la requête SQL avec le prompt échappé
            llm_query = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                   '{prompt_escaped}'
                ) AS adapted_steps
            """

            llm_response = self.session.sql(llm_query)
            llm_response = parse_query_result(llm_response)
            parsed_steps = llm_response[0]["ADAPTED_STEPS"].strip().split("\n")

            new_steps = []
            notes = []
            for step in parsed_steps:
                if len(step) > 0:
                    if step[0].isdigit():
                        new_steps.append(step)
                    elif str.startswith(step.lower(), "note"):
                        notes.append(step[6:].strip())
            return new_steps, notes

        except Exception as e:
            logging.error(f"Failure:  Error found with recipe adaptation steps with substitution transformation made by LLM. Error: {str(e)}. Traceback: {traceback.format_exc()}")
            # Fallback: simple manual adaptation
            adapted_steps = recipe.steps
            adapted_steps = [
                step.replace(original, substitute)
                for original, substitute in substitutions.items()
                for step in adapted_steps
            ]
            return adapted_steps, []

    def adapt_recipe_delete(self, recipe: Recipe, ingredients_to_delete: List[str]) -> Tuple[List[str], List[str]]:
        """
        Adapt the recipe steps by deleting ingredients via LLM.
        Returns: (new_steps, notes)
        """

        base_prompt = f"""You are an expert chef specializing in recipe adaptation for ingredient deletion.
        ORIGINAL RECIPE:
        Name: {recipe.name}
        Ingredients: {recipe.ingredients}
        Steps: {recipe.steps}

        INGREDIENTS TO REMOVE:
        """

        for ing in ingredients_to_delete:
            base_prompt += f"- Remove '{ing}'\n"

        base_prompt += """
        YOUR TASK:
        Adapt the recipe steps to REMOVE these ingredients while maintaining the dish's quality and integrity.

        ADAPTATION GUIDELINES:
        1. Modify ONLY the preparation steps that are affected by the deletions
        2. Remove all mentions of the deleted ingredients from the steps
        2. Preserve the original step numbering and structure
        5. Note any texture or consistency changes that may occur
        6. Suggest technique modifications if needed (e.g., mixing methods, prep techniques)
        7. Keep instructions clear, concise, and actionable
        8. Maintain the same cooking skill level as the original recipe

        IMPORTANT CONSIDERATIONS:
        - If multiple steps use the same deleted ingredient, ensure consistency across all adaptations
        - Do not add new steps; only modify or delete existing ones.
        - Do not change unaffected steps
        - Do NOT add new ingredients no matter what. Even if the recipe does not seem coherent to you.

        OUTPUT FORMAT:
        Provide only the adapted recipe steps in numbered format.

        ADAPTED RECIPE STEPS:"""

        try:
            prompt_escaped = base_prompt.replace("'", "''")

            llm_query = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                   '{prompt_escaped}'
                ) AS adapted_steps
            """

            llm_response = self.session.sql(llm_query)
            llm_response = parse_query_result(llm_response)
            parsed_steps = llm_response[0]["ADAPTED_STEPS"].strip().split("\n")

            new_steps: List[str] = []
            notes: List[str] = []

            for step in parsed_steps:
                if step:
                    if step[0].isdigit():
                        new_steps.append(step)
                    elif step.lower().startswith("note"):
                        # handles "Note:" or "note:"
                        notes.append(step.split(":", 1)[-1].strip())

            return new_steps, notes

        except Exception as e:
            logging.error(f"Failure:  Error found with recipe adaptation steps for deletion transformation made by LLM. Error: {str(e)}. Traceback: {traceback.format_exc()}")

            # Fallback: naive removal of ingredient words in steps
            adapted_steps = list(recipe.steps)
            for ing in ingredients_to_delete:
                adapted_steps = [step.replace(ing, "").strip() for step in adapted_steps]

            return adapted_steps, []

    def transform(
            self,
            recipe: Recipe,
            ingredients_to_remove: List[str],
            constraints: TransformConstraints)-> TransformResponse:
        """
        Transform a recipe based on constraints and ingredients to remove, full pipeline
        """
        success = True
        
        try:
            # Step 1: Find ingredient to 'transform' depending on constraints if not received
            transformation_type = constraints.transformation
            if ingredients_to_remove is not None:
                ingredients_to_transform = ingredients_to_remove
            else:
                ingredients_to_transform = self._extract_ingredients_from_text(recipe, constraints)
                # TODO : code à rajouter 

            logging.info("Success: Step 1 finished (Ingredients to remove has been found).")

            transformations = {}
            transformation_count = 0
            new_recipe_score = 0.0
            base_ingredients = [ing for ing in recipe.ingredients if ing not in ingredients_to_transform]

            new_recipe = Recipe(
                id=recipe.id,
                name=recipe.name,
                serving_size=recipe.serving_size,
                servings=recipe.servings,
                health_score=new_recipe_score,
                ingredients=base_ingredients,
                quantity_ingredients=recipe.quantity_ingredients,
                minutes=recipe.minutes,
                steps=recipe.steps,
            )
            new_ingredients = recipe.ingredients # default value
            new_recipe_nutrition = NutritionDelta()
            # Pipeline diversion based on transformation type
            if transformation_type == TransformationType.SUBSTITUTION:
                # Step 2 : Find substitutes for ingredients to transform, function returns new recipe health score as well.
                if self.pca_data is None:
                    self.load_pca_data()
                ingredients_to_substitute_matched = [
                    self.ingredients_cache[ing]["name"] 
                    for ing in ingredients_to_transform]
                
                for original_ing, matched_name in zip(ingredients_to_transform, ingredients_to_substitute_matched):
                    substitute, was_substituted , new_recipe_nutrition = self.substitute_ingr(matched_name, constraints, base_ingredients, recipe.id, recipe.serving_size, recipe.servings)
                    if was_substituted:
                        transformations[original_ing] = substitute
                        transformation_count += 1
                new_ingredients = [transformations.get(ingredient, ingredient) for ingredient in recipe.ingredients]
                new_recipe_score = new_recipe_nutrition.health_score
                logging.info("Success: Step 2 finished for Substitution (Subtitute ingredients found for eache ingredients to remove).")
                # Step 3 : Adapt recipe step with LLM
                if transformations:
                    new_recipe.steps, notes = self.adapt_recipe_with_llm(new_recipe, transformations)
                logging.info("Success: Step 3 finished for Substitution (LLM's adapted new_recipe steps successfully).")

            elif transformation_type == TransformationType.ADD:
                # TODO
                pass
            elif transformation_type == TransformationType.DELETE and ingredients_to_transform:
                # Step 2 : Delete ingredients from recipe, calculate health score after deletion
                new_recipe_nutrition = self.compute_recipe_nutrition_totals(
                recipe_id=recipe.id,
                ingredients=base_ingredients,
                serving_size=recipe.serving_size,
                servings=recipe.servings
                )
                denom = (recipe.serving_size or 0) * (recipe.servings or 0)
                if denom > 0:
                    scaled_nutrition = self.scale_nutrition(
                    new_recipe_nutrition,
                    factor=100.0 / denom
                    )
                else :
                    scaled_nutrition = new_recipe_nutrition ## fallback servings null
                new_recipe_score = self.compute_rhi(scaled_nutrition)
                new_recipe_nutrition.health_score = new_recipe_score
                logging.info("Success: Step 2 finished for Deletion (Removed successfully unwanted ingredients and computed new health score).")
                # Step 3 : Adapt recipe step with LLM
                new_recipe.steps, notes= self.adapt_recipe_delete(recipe, ingredients_to_transform)
                logging.info("Success: Step 3 finished for Deletion (LLM's adapted new_recipe steps successfully).")

            # Step 4 : Build output
            original_nutrition = self.compute_recipe_nutrition_totals(
                recipe_id=recipe.id,
                ingredients=recipe.ingredients,
                serving_size=recipe.serving_size,
                servings=recipe.servings
            )
            original_nutrition.health_score = recipe.health_score
            response = TransformResponse(
                recipe=new_recipe,
                original_name=recipe.name,
                transformed_name=new_recipe.name,
                substitutions=None,
                nutrition_before=original_nutrition,
                nutrition_after=new_recipe_nutrition,
                success=success,
                message="\n".join(notes),
            )
            logging.info("Success: Step 4 finished (TransformerResponse successfully built, returning it...).")
            return response

        except Exception as e:
            logging.error(f"Failure: Transform function failed. Error: {str(e)}. Traceback: {traceback.format_exc()}")
            success = False
            response = TransformResponse(
                recipe=recipe,
                original_name=recipe.name,
                transformed_name=recipe.name,
                substitutions=None,
                nutrition_before=None,
                nutrition_after=None,
                success=success,
                message=None,
            )
        logging.error("Returning default response with input recipe.")
        return response
