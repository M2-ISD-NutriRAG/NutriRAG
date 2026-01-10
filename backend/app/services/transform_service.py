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
ADD_CONSTRAINT_TO_NUTRIENT = {
    "increase_protein": "PROTEIN_G",
    "increase_fiber": "FIBER_G",
    "decrease_sodium": "SODIUM_MG",
    "decrease_sugar": "SUGAR_G",
    "decrease_calories": "ENERGY_KCAL",
}


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
        #self.load_pca_data()
        self.recipe_tags_cache: Dict[str, Dict[str, Optional[Dict[str, Any]]]] = {}

    def _zero_nutrition(self) -> NutritionDelta:
        return NutritionDelta(
            calories=0.0, protein_g=0.0, fat_g=0.0, saturated_fats_g=0.0,
            carb_g=0.0, fiber_g=0.0, sugar_g=0.0, sodium_mg=0.0,
            calcium_mg=0.0, iron_mg=0.0, magnesium_mg=0.0, potassium_mg=0.0,
            vitamin_c_mg=0.0, health_score=0.0
        )

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
                out[(ing or "").strip().lower()] = float(qty) if qty is not None else None

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

            recipe_nutrition.calories += nutrition["ENERGY_KCAL"] * factor
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
            recipe_nutrition.vitamin_c_mg += nutrition["VITC_MG"] * factor

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
    
    def judge_substitute(self, candidates, recipe_ingredients: List[str], recipe_id: int, serving_size: float, servings: float) -> Tuple[str,NutritionDelta]:
        """
        Final ingredient choice between list of candidates

        Args:
            candidates: list of possible ingredients to substitute with (extracted from get_neighbors_pca() )
            recipe_id, serving_size, servings, recipe_ingredients: recipe information
        Returns:
            ingredient_id
        """
        if not candidates:
            logging.warning("Failure: No candidatee found.")
            return None, self._zero_nutrition()
        best_ing = None
        best_nutrition = self._zero_nutrition()
        for cand in candidates:
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
            return ingredient, False, self._zero_nutrition()

        candidates = result["best_substitutes"]
        substitute, nutrition = self.judge_substitute(candidates, recipe_ingredients, recipe_id, serving_size, servings)

        if substitute:
            substitute_name = substitute["name"]
            logging.info(f"Success: Found substitute for {ingredient} → {substitute_name} (PCA score: {substitute['global_score']:.3f})")
            return substitute_name, True, nutrition
        
        return ingredient, False, self._zero_nutrition()

    def fetch_ingredients_tags(self, recipe_id: str, ingredients: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Returns mapping:
          key = LOWER(TRIM(ingredient_from_recipe_name))
          val = dict of tag columns (or None if not found)
        Cached per recipe+ingredient key.
        """
        if recipe_id not in self.recipe_tags_cache:
            self.recipe_tags_cache[recipe_id] = {}

        keys = [(s or "").strip().lower() for s in ingredients]
        keys = [k for k in keys if k]
        unique_keys = sorted(set(keys))

        missing = [k for k in unique_keys if k not in self.recipe_tags_cache[recipe_id]]
        if not missing:
            return self.recipe_tags_cache[recipe_id]

        # Default missing keys to None so we don't re-query forever
        for k in missing:
            self.recipe_tags_cache[recipe_id][k] = None

        im = self.session.table("NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING")
        it = self.session.table("NUTRIRAG_PROJECT.CLEANED.INGREDIENTS_TAGGED")

        ing_key_expr = lower(trim(col("INGREDIENT_FROM_RECIPE_NAME")))

        joined = (
            im.filter(col("RECIPE_ID") == recipe_id)
              .with_column("ING_KEY", ing_key_expr)
              .filter(col("ING_KEY").isin(missing))
              .join(it, col("INGREDIENT_ID") == col("NDB_NO"), how="left")
              .select(
                  col("ING_KEY"),
                  col("NDB_NO"),
                  col("DESCRIP"),
                  col("FOODON_LABEL"),
                  col("IS_DAIRY"),
                  col("IS_GLUTEN"),
                  col("CONTAINS_NUTS"),
                  col("IS_GRAIN"),
                  col("IS_SEAFOOD"),
                  col("IS_SWEETENER"),
                  col("IS_VEGETABLE"),
                  col("IS_VEGETARIAN"),
              )
        )

        # If multiple rows exist per ING_KEY, just take the first one deterministically
        w = Window.partition_by(col("ING_KEY")).order_by(col("NDB_NO").asc_nulls_last())
        ranked = joined.with_column("RN", row_number().over(w)).filter(col("RN") == 1)

        rows = ranked.collect()

        for r in rows:
            ing_key = r["ING_KEY"]
            self.recipe_tags_cache[recipe_id][ing_key] = {
                "NDB_NO": r["NDB_NO"],
                "DESCRIP": r["DESCRIP"],
                "FOODON_LABEL": r["FOODON_LABEL"],
                "IS_DAIRY": r["IS_DAIRY"],
                "IS_GLUTEN": r["IS_GLUTEN"],
                "CONTAINS_NUTS": r["CONTAINS_NUTS"],
                "IS_GRAIN": r["IS_GRAIN"],
                "IS_SEAFOOD": r["IS_SEAFOOD"],
                "IS_SWEETENER": r["IS_SWEETENER"],
                "IS_VEGETABLE": r["IS_VEGETABLE"],
                "IS_VEGETARIAN": r["IS_VEGETARIAN"],
            }

        return self.recipe_tags_cache[recipe_id]

    def identify_ingredients_to_remove_by_algo(
        self, 
        recipe: Recipe, 
        constraints: TransformConstraints
    ) -> List[str]:
        """
        Algorithm to identify ingredients to remove based on nutritional constraints.
        
        Args:
            recipe: Recipe object
            constraints: TransformConstraints with nutritional goals
            
        Returns:
            List of ingredient names to remove
        """
        ingredients_to_remove = []
        
        try:
            # Fetch nutritional data for all ingredients
            ingredients_nutrition = self.fetch_ingredients_nutrition(
                recipe.id, 
                recipe.ingredients
            )
            ingredients_tags = self.fetch_ingredients_tags(recipe.id, recipe.ingredients)

            allergy_constraints = [ 'no_lactose', 'no_gluten', 'no_nuts', 'vegetarian', 'vegan' ]
            reduction_constraints = [ 'decrease_sugar', 'decrease_sodium', 'decrease_calories', 'decrease_carbs', 'increase_protein', 'decrease_protein' ]

            active_allergy = any(getattr(constraints, c, False) for c in allergy_constraints)
            active_reduction = any(getattr(constraints, c, False) for c in reduction_constraints)

            max_items = 3 if active_allergy else (1 if active_reduction else 0)

            # Define thresholds to identify "bad" ingredients
            SUGAR_THRESHOLD = 10.0  # g per 100g
            SODIUM_THRESHOLD = 500.0  # mg per 100g
            SATURATED_FAT_THRESHOLD = 5.0  # g per 100g
            CALORIE_THRESHOLD = 300.0  # kcal per 100g
            CARB_THRESHOLD = 50.0  # g per 100g
            
            for ingredient in recipe.ingredients:
                ing_key = ingredient.lower().strip()
                nutrition = ingredients_nutrition.get(ing_key)
                
                if nutrition is None:
                    continue
                
                should_remove = False
                
                # Check reduction constraints
                if constraints.decrease_sugar and nutrition.get("SUGAR_G", 0) > SUGAR_THRESHOLD:
                    should_remove = True
                    #print(f"_identify_ingredients_to_remove_by_algo: {ingredient} identified for sugar reduction ({nutrition.get('SUGAR_G', 0):.1f}g)")
                
                if constraints.decrease_sodium and nutrition.get("SODIUM_MG", 0) > SODIUM_THRESHOLD:
                    should_remove = True
                    #print(f"_identify_ingredients_to_remove_by_algo: {ingredient} identified for sodium reduction ({nutrition.get('SODIUM_MG', 0):.1f}mg)")
                
                if constraints.decrease_calories and nutrition.get("ENERGY_KCAL", 0) > CALORIE_THRESHOLD:
                    should_remove = True
                    #print(f"_identify_ingredients_to_remove_by_algo: {ingredient} identified for calorie reduction ({nutrition.get('ENERGY_KCAL', 0):.1f}kcal)")
                
                if constraints.decrease_carbs and nutrition.get("CARB_G", 0) > CARB_THRESHOLD:
                    should_remove = True
                    #print(f"_identify_ingredients_to_remove_by_algo: {ingredient} identified for carbohydrate reduction ({nutrition.get('CARB_G', 0):.1f}g)")
                
                # Check dietary constraints (via PCA data if available)
                tags = ingredients_tags.get(ing_key)
                if tags is not None:
                    if constraints.no_lactose and tags.get("IS_DAIRY") is True:
                        should_remove = True
                    if constraints.no_gluten and tags.get("IS_GLUTEN") is True:
                        should_remove = True
                    if constraints.no_nuts and tags.get("CONTAINS_NUTS") is True:
                        should_remove = True
                    if constraints.vegetarian and tags.get("IS_VEGETARIAN") is False:
                        should_remove = True
                    if constraints.vegan and tags.get("IS_VEGETABLE") is False:
                        should_remove = True  # proxy as you requested

                if should_remove:
                    ingredients_to_remove.append(ingredient)
                    if max_items and len(ingredients_to_remove) >= max_items:
                        break
            
            # Limit the number of ingredients to remove (max 3 to not destroy the recipe)
            if len(ingredients_to_remove) > 3:
                print(f"_identify_ingredients_to_remove_by_algo: Limiting to 3 ingredients out of {len(ingredients_to_remove)} identified")
                ingredients_to_remove = ingredients_to_remove[:3]
            
            return ingredients_to_remove
            
        except Exception as e:
            print(f" Error in identifying ingredients to remove: {e}")
            traceback.print_exc()
            return []

    def _map_add_constraint_to_nutrient(
            self, constraint_name: str
    ) -> Optional[str]:
        """
        Maps an ADD constraint to the corresponding nutrient column.
        Returns None if the constraint is not supported.
        """
        return self.ADD_CONSTRAINT_TO_NUTRIENT.get(constraint_name)

    def _get_active_add_constraint(self, constraints: TransformConstraints) -> Optional[str]:
        for c in [
            "increase_protein",
            "increase_fiber",
            "decrease_sodium",
            "decrease_sugar",
            "decrease_calories",
        ]:
            if getattr(constraints, c, False):
                return c
        return None

    def _infer_role_from_tags(self, tags: Dict[str, Any]) -> str:
        if not tags:
            return "other"
        if tags.get("IS_SEAFOOD"):
            return "animal_protein"
        if tags.get("IS_VEGETARIAN") is False:
            return "animal_protein"
        if tags.get("IS_GRAIN"):
            return "carb"
        if tags.get("IS_SWEETENER"):
            return "sugar"
        if tags.get("IS_VEGETABLE"):
            return "plant"
        return "other"

    def identify_ingredients_to_remove_by_llm(
        self, 
        recipe: Recipe, 
        constraints: TransformConstraints
    ) -> List[str]:
        """
        LLM fallback to identify ingredients to remove if the algorithm fails, based on full recipe and constraints.
        If constraint is an allergy or regime specific (vegetarian, vegan) all ingredients to remove are returned
        If constraint is a reduction (sugar, sodium, calories, carbs, protein) only one ingredient is returned
        
        Args:
            recipe: Recipe object
            constraints: TransformConstraints with nutritional goals
            
        Returns:
            List of ingredient names to remove
        """
        try:
            allergy_constraints = [ 'no_lactose', 'no_gluten', 'no_nuts', 'vegetarian', 'vegan' ]
            reduction_constraints = [ 'decrease_sugar', 'decrease_sodium', 'decrease_calories', 'decrease_carbs', 'increase_protein', 'decrease_protein' ]
            
            active_allergy = [c for c in allergy_constraints if getattr(constraints, c, False)]
            active_reduction = [c for c in reduction_constraints if getattr(constraints, c, False)]

            if not active_allergy and not active_reduction:
                return []
            
            if active_allergy:
                mode = "ALL_VIOLATIONS"
                constraints_text = ", ".join(active_allergy + active_reduction)
            else:
                max_items = 1
                mode = "ONE_OFFENDER"
                constraints_text = ", ".join(active_reduction)
            logging.info("boo")
            base_prompt = f"""
            
            You are a culinary and nutrition expert analyzing recipe ingredients.

                YOUR TASK:
                - Analyze the recipe as a whole (name, ingredients, quantities, and steps).
                - Identify which ingredients should be REMOVED to meet the constraints.
                If constraint are no lactose, no_gluten, no_nuts, vegetarian, vegan, return ingredients that obviously violate these constraints.
                - For no lactose: only flag ingredients that are dairy by name. Do NOT flag hidden dairy (bread, crescent rolls, eggs etc.)
                - For vegetarian/vegan, only remove ingredients that are clearly non-vegetarian/vegan by name (meat, fish, poultry, eggs, dairy, etc.)
                - If constraint are to decrease sugar, sodium, calories, carbs, or protein, return one ingredient that most harms the constraints.

                IMPORTANT:
                - Only suggest removing ingredients that clearly violate the constraints
                - Do NOT suggest removing essential ingredients that define the dish
                - Be conservative - better to remove fewer ingredients than too many
                - You MUST choose ONLY from the Ingredients list exactly (no synonyms / no variants).
                - If no ingredients violate the constraints, respond with NONE.
                
                STRICT OUTPUT RULES (MANDATORY):
                - Output ONLY either:
                  (A) NONE
                  OR
                  (B) a comma-separated list of ingredient strings copied EXACTLY from RECIPE INGREDIENTS.
                - NO other words. NO explanations. NO punctuation other than commas.
                - NO prefixes like "Explanation:" or "Ingredients:".
                - If nothing should be removed, output EXACTLY: NONE
                Example: cheese, butter
            
                If no ingredients should be removed, output: NONE
            
            RECIPE: 
            Name: {recipe.name}
            Ingredients: {', '.join(recipe.ingredients)}
            Quantities: {recipe.quantity_ingredients}
            Steps:
            {chr(10).join(recipe.steps)}
            
            CONSTRAINTS (booleans): {constraints.__dict__}
            ANSWER:
            DON'T add extra ingredients to remove. Just follow the constraints and be brief.
            """

            prompt_escaped = base_prompt.replace("'", "''")
            
            llm_query = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                   '{prompt_escaped}'
                ) AS INGREDIENTS_TO_REMOVE
            """
            res = self.session.sql(llm_query).collect()
            if not res:
                return []

            response_text = (res[0]["INGREDIENTS_TO_REMOVE"] or "").strip()
            if not response_text or response_text.upper() == "NONE":
                print("LLM: No ingredients to remove")
                return []
                        
            # Parse the ingredient list (handle different formats)
            ingredients_to_remove = []
            
            # Clean the response from special characters and numbers
            cleaned_response = response_text.replace("\n", ",").replace(";", ",")
            
            for item in cleaned_response.split(","):
                # Clean each item
                cleaned_item = item.strip()
                if not cleaned_item:
                    continue
                # Remove leading numbers (e.g., "1. sugar" -> "sugar")
                if cleaned_item[0].isdigit():
                    cleaned_item = cleaned_item.lstrip("0123456789.-) ").strip()
                
                if len(cleaned_item) > 1:
                    # Verify that the ingredient exists in the recipe (fuzzy matching)
                    matched = False
                    for recipe_ing in recipe.ingredients:
                        if cleaned_item.lower() in recipe_ing.lower() or recipe_ing.lower() in cleaned_item.lower():
                            if recipe_ing not in ingredients_to_remove:
                                ingredients_to_remove.append(recipe_ing)
                            matched = True
                            break
                    
                    if not matched:
                        print(f"LLM: Ingredient '{cleaned_item}' not found in recipe")
            
                if len(ingredients_to_remove) >= 3:
                    break
            return ingredients_to_remove
            
        except Exception as e:
            print(f"LLM error for ingredient identification: {e}")
            traceback.print_exc()
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
            logging.info(f"LLM response: {llm_response}")
            llm_response = parse_query_result(llm_response)
            response_text = llm_response[0]["ADAPTED_STEPS"].strip()
            
            # Verification of LLM output format
            if not response_text:
                print("LLM returned an empty response")
                return recipe.steps, []
            
            parsed_steps = response_text.split("\n")

            new_steps = []
            notes = []
            
            for step in parsed_steps:
                step_cleaned = step.strip()
                if not step_cleaned:
                    continue
                
                # Check if it's a numbered step (format: "1.", "1)", or just a digit at the beginning)
                if step_cleaned[0].isdigit() or step_cleaned.startswith("-") or step_cleaned.startswith("*"):                    # Clean list formats
                    cleaned_step = step_cleaned.lstrip("0123456789.-*) ").strip()
                    if cleaned_step:
                        new_steps.append(cleaned_step)
                elif step_cleaned.lower().startswith("note"):
                    # Extract the note after "Note:"
                    note_content = step_cleaned.split(":", 1)[-1].strip()
                    if note_content:
                        notes.append(note_content)
            
            # Validation: if no steps were extracted, fallback to original steps
            if not new_steps:
                print("LLM: No valid steps extracted, using original steps")
                return recipe.steps, notes
            
            print(f"LLM: {len(new_steps)} adapted steps, {len(notes)} notes")
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
            response_text = llm_response[0]["ADAPTED_STEPS"].strip()
            
            # Verification of LLM output format
            if not response_text:
                print("LLM returned an empty response -> adapt_recipe_delete")
                return recipe.steps, []
            
            parsed_steps = response_text.split("\n")

            new_steps: List[str] = []
            notes: List[str] = []

            for step in parsed_steps:
                step_cleaned = step.strip()
                if not step_cleaned:
                    continue
                
                # Check if it's a numbered step

                if step_cleaned[0].isdigit() or step_cleaned.startswith("-") or step_cleaned.startswith("*"):                    # Clean list formats
                    cleaned_step = step_cleaned.lstrip("0123456789.-*) ").strip()
                    if cleaned_step:
                        new_steps.append(cleaned_step)
                elif step_cleaned.lower().startswith("note"):
                    # Extract the note after "Note:"
                    note_content = step_cleaned.split(":", 1)[-1].strip()
                    if note_content:
                        notes.append(note_content)
            
            # Validation: if no steps were extracted, fallback to original steps
            if not new_steps:
                print("LLM: No valid steps extracted, using original steps -> adapt_recipe_delete")
                return recipe.steps, notes
            
            print(f"LLM: {len(new_steps)} adapted steps, {len(notes)} notes")
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
            notes = []
            # Step 1: Find ingredient to 'transform' depending on constraints if not received
            transformation_type = constraints.transformation
            if ingredients_to_remove is not None:
                ingredients_to_transform = ingredients_to_remove
            else:
                # Algorithm in priority to identify ingredients
                print("Step 1a: Identification by algorithm...")
                ingredients_to_transform = self.identify_ingredients_to_remove_by_algo(recipe, constraints)
                
                # LLM fallback if the algorithm finds nothing
                if not ingredients_to_transform:
                    print("Step 1b: LLM fallback for identification...")
                    ingredients_to_transform = self.identify_ingredients_to_remove_by_llm(recipe, constraints)
                
                if not ingredients_to_transform:
                    print("No ingredients to transform identified")
                else:
                    print(f"Ingredients identified: {ingredients_to_transform}")

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
            new_recipe_nutrition = self._zero_nutrition()
            # Pipeline diversion based on transformation type
            if transformation_type == TransformationType.SUBSTITUTION:

                # Step 2 : Find substitutes for ingredients to transform, function returns new recipe health score as well.
                if self.pca_data is None:
                    self.load_pca_data()
                  # Use cache match when available, otherwise just use the recipe ingredient string
                ingredients_to_substitute_matched = [
                    (self.ingredients_cache.get(ing) or {}).get("name", ing)
                    for ing in ingredients_to_transform
                ]

                working_ingredients = list(base_ingredients)

                for original_ing, matched_name in zip(ingredients_to_transform, ingredients_to_substitute_matched):
                    substitute, was_substituted, new_recipe_nutrition = self.substitute_ingr(
                        matched_name,
                        constraints,
                        working_ingredients,
                        recipe.id,
                        recipe.serving_size,
                        recipe.servings
                    )
                    if was_substituted:
                        transformations[original_ing] = substitute
                        transformation_count += 1

                        # Update the working ingredient list for the next iteration
                        # (replace original_ing if it still exists, otherwise just append substitute)
                        if original_ing in working_ingredients:
                            working_ingredients = [substitute if x == original_ing else x for x in working_ingredients]
                        else:
                            working_ingredients.append(substitute)

                        # Apply substitutions to the full recipe ingredient list
                        new_ingredients = [transformations.get(ingredient, ingredient) for ingredient in recipe.ingredients]
                        new_recipe.ingredients = new_ingredients

                        # Trust the nutrition returned by the last substitute_ingr call (now based on updated working_ingredients)
                        new_recipe_score = new_recipe_nutrition.health_score
                        new_recipe.health_score = new_recipe_score

                        logging.info("Success: Step 2 finished for Substitution (Subtitute ingredients found for eache ingredients to remove).")
               
                # Step 3 : Adapt recipe step with LLM
                if transformations:
                    new_recipe.steps, notes = self.adapt_recipe_with_llm(new_recipe, transformations)
                logging.info("Success: Step 3 finished for Substitution (LLM's adapted new_recipe steps successfully).")

            # elif transformation_type == TransformationType.ADD:
            #     # TODO
            #     pass
            elif transformation_type == TransformationType.ADD:

                # 1 Identifier la contrainte ADD active
                active_constraint = self._get_active_add_constraint(constraints)
                if not active_constraint:
                    notes.append("No ADD constraint provided.")
                    new_recipe_nutrition = self._zero_nutrition()
                    new_recipe_score = recipe.health_score
                    new_recipe.health_score = new_recipe_score

                else:
                    # 2 Nutriment cible à optimiser
                    target_nutrient = self._map_add_constraint_to_nutrient(active_constraint)
                    if not target_nutrient:
                        notes.append(f"Unsupported ADD constraint: {active_constraint}")
                        new_recipe_nutrition = self._zero_nutrition()
                        new_recipe_score = recipe.health_score
                        new_recipe.health_score = new_recipe_score

                    else:
                        # 3 Nutrition actuelle de la recette
                        base_nutrition = self.get_health_score(
                            recipe.ingredients,
                            recipe.id,
                            recipe.serving_size,
                            recipe.servings
                        )

                        # 4 Déterminer les rôles nutritionnels déjà présents
                        recipe_tags = self.fetch_ingredients_tags(recipe.id, recipe.ingredients)
                        existing_roles = set()
                        for ing in recipe.ingredients:
                            tags = recipe_tags.get((ing or "").strip().lower())
                            role = self._infer_role_from_tags(tags)
                            existing_roles.add(role)

                        # 5 Charger PCA si nécessaire
                        if self.pca_data is None:
                            self.load_pca_data()

                        df = self.pca_data.copy()

                        # 6 Appliquer les contraintes alimentaires
                        if constraints.no_lactose:
                            df = df[df["is_lactose"] == 0]
                        if constraints.no_gluten:
                            df = df[df["is_gluten"] == 0]
                        if constraints.no_nuts:
                            df = df[df["contains_nuts"] == 0]
                        if constraints.vegetarian:
                            df = df[df["is_vegetarian"] == 1]
                        if constraints.vegan:
                            df = df[df["is_vegetable"] == 1]

                        # 7 Filtrage nutritionnel guidé par la contrainte
                        median_value = df[target_nutrient].median()
                        if active_constraint.startswith("increase"):
                            df = df[df[target_nutrient] > median_value]
                        else:  # decrease_xxx
                            df = df[df[target_nutrient] < median_value]

                        # 8 Anti-redondance culinaire + constitution des candidats
                        candidates = []
                        for _, row in df.iterrows():
                            cand_name = row["Descrip"]

                            cand_tags = {
                                "IS_SEAFOOD": row.get("is_seafood", False),
                                "IS_GRAIN": row.get("is_gluten", False),
                                "IS_SWEETENER": row.get("is_sweetener", False),
                                "IS_VEGETABLE": row.get("is_vegetable", False),
                                "IS_VEGETARIAN": row.get("is_vegetarian", True),
                            }

                            cand_role = self._infer_role_from_tags(cand_tags)

                            if cand_role not in existing_roles:
                                candidates.append({"name": cand_name})

                            if len(candidates) >= 15:
                                break

                        # 9️⃣ Sélection finale par gain marginal de RHI
                        best_ing, best_nutrition = self.judge_substitute(
                            candidates,
                            recipe.ingredients,
                            recipe.id,
                            recipe.serving_size,
                            recipe.servings
                        )

                        if best_ing:
                            added_ingredient = best_ing["name"]
                            new_ingredients = recipe.ingredients + [added_ingredient]
                            new_recipe.ingredients = new_ingredients

                            new_recipe_nutrition = best_nutrition
                            new_recipe_score = best_nutrition.health_score
                            new_recipe.health_score = new_recipe_score

                            notes.append(f"Added ingredient: {added_ingredient}")

                        else:
                            new_recipe_nutrition = base_nutrition
                            new_recipe_score = base_nutrition.health_score
                            new_recipe.health_score = new_recipe_score
                            notes.append("No suitable ingredient found to add.")


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
