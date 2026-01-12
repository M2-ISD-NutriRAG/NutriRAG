################################################################################################################

#                                        Transform service interface

################################################################################################################
import json
import traceback
import pandas as pd
import numpy as np
import threading
import logging
import decimal

from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel

from snowflake.snowpark.functions import col, lower, trim, row_number
from snowflake.snowpark.window import Window
from snowflake.snowpark import Session


class TransformationType(Enum):
    ADD = 0
    DELETE = 1
    SUBSTITUTION = 2


class TransformConstraints(BaseModel):
    # Constraints for recipe transformation
    transformation: TransformationType
    no_lactose: bool = False
    no_gluten: bool = False
    no_nuts: bool = False
    vegetarian: bool = False
    vegan: bool = False
    increase_protein: bool = False
    decrease_sugar: bool = False
    decrease_protein: bool = False
    decrease_carbs: bool = False
    decrease_calories: bool = False
    decrease_sodium: bool = False
    decrease_satfat: bool = False
    increase_fiber: bool = False



class Recipe(BaseModel):
    id: int
    name: str
    serving_size: float
    servings: float
    health_score: float
    ingredients: List[str]
    quantity_ingredients: List[str]
    minutes: float
    steps: List[str]


class TransformRequest(BaseModel):
    # Transform request body
    recipe: Recipe
    ingredients_to_remove: Optional[List[str]] = None
    ingredients_to_add: Optional[List[str]] = None
    constraints: Optional[TransformConstraints] = None


class Substitution(BaseModel):
    # Single ingredient substitution
    original_ingredient: str
    substitute_ingredient: str
    original_quantity: Optional[float] = None
    substitute_quantity: Optional[float] = None
    reason: str = ""


class NutritionDelta(BaseModel):
    # Changes in nutrition values
    calories: float = 0.0
    protein_g: float = 0.0
    saturated_fats_g: float = 0.0
    fat_g: float = 0.0
    carb_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    sugar_g: float = 0.0
    iron_mg: float = 0.0
    calcium_mg: float = 0.0
    magnesium_mg: float = 0.0
    potassium_mg: float = 0.0
    vitamin_c_mg: float = 0.0
    health_score: float = 0.0


class TransformResponse(BaseModel):
    # Transform response
    recipe: Recipe
    original_name: str
    transformed_name: str
    substitutions: Optional[List[Substitution]] = None
    nutrition_before: Optional[NutritionDelta] = None
    nutrition_after: Optional[NutritionDelta] = None
    success: bool = True
    message: Optional[str] = None


################################################################################################################

#                                               Utilitaires

################################################################################################################


def parse_procedure_result(query_result, proc_name) -> Any:
    """
    Parse a procedure result parsed with query result to be usable.
    Args:
        query_result: query result parsed
        proc_name: procedure name

    Returns:
        output: Any
    """
    value = query_result[0][proc_name]
    output = json.loads(value)
    return output


def parse_query_result(query_result) -> List[Dict[str, float]]:
    """
    Collect query result and return as dict list
    Args:
        query_result : result of a query call (session.sql(query))

    Returns:
        List[Dict[str, float]]: formatted output
    """
    collected_result = query_result.collect()
    return [row.as_dict() for row in collected_result]


def format_output(input: Any) -> str:
    """
    Dumps output in json format to be usable.
    Args:
        input: Any type of data
    Returns:
        str: json result of the formatted output
    """
    # Convertir les Decimal en float pour la sérialisation JSON
    if (
        isinstance(input, list)
        and len(input) > 0
        and isinstance(input[0], dict)
    ):
        from decimal import Decimal

        for item in input:
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)

    # Retourner en JSON
    return json.dumps(input, indent=2)


def to_dict(obj):
    """Recursively convert an object and its nested objects to dictionaries"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_dict(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return {key: to_dict(value) for key, value in vars(obj).items()}
    else:
        return obj


################################################################################################################

#                                        Transform service logic

################################################################################################################
NUTRIENT_BASIS_GRAMS = 100
NUTRITION_COLS = [
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
]
INGREDIENTS_QUANTITY_TABLE_NAME = "NUTRIRAG_PROJECT.RAW.INGREDIENTS_QUANTITY"
INGREDIENTS_CLUSTERING_TABLE_NAME = "NUTRIRAG_PROJECT.ANALYTICS.INGREDIENTS_WITH_CLUSTERS"
INGREDIENTS_MATCHED_TABLE_NAME = "NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING"
INGREDIENTS_NUTRIMENTS_TABLE_NAME = "NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS"
INGREDIENTS_TAGGED_TABLE_NAME = "NUTRIRAG_PROJECT.CLEANED.INGREDIENTS_TAGGED"
LOG_RECIPE_TABLE_NAME = "NUTRIRAG_PROJECT.ANALYTICS.LOG_TRANSFORMATION"

ADD_CONSTRAINT_TO_NUTRIENT = {
    "increase_protein": "PROTEIN_G",
    "decrease_protein": "PROTEIN_G",
    "increase_fiber": "FIBER_G",
    "decrease_sugar": "SUGAR_G",
    "decrease_carbs": "CARB_G",
    "decrease_calories": "ENERGY_KCAL",
    "decrease_sodium": "SODIUM_MG",
    "decrease_satfat": "SATURATED_FATS_G",
}

class TransformService:
    _pca_data_cache = None
    _pca_lock = threading.Lock()

    # check if async necessary for the constructor
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.matched_ingredients_cache: Dict[str, Optional[Dict]] = {}
        self.pca_data = None  # ingredient coordinates for clustering
        self.recipe_tags_cache: Dict[
            str, Dict[str, Optional[Dict[str, Any]]]
        ] = {}
        self.log_msg: List[str] = []

    def _zero_nutrition(self) -> NutritionDelta:
        return NutritionDelta(
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
            health_score=0.0,
        )

    def clean_ingredient_name(self, ingredient_name: str) -> str:
        return ingredient_name.lower().strip().replace("'", "''")

    def get_ingredient_matched(
        self, ingredient_name_list: List[str]
    ) -> List[Optional[Dict]]:
        """
        Récupère les informations nutritionnelles d'un seul ingrédient depuis la base

        Args:
            ingredient_name: Nom de l'ingrédient à chercher

        Returns:
            Dict avec les infos nutritionnelles ou None si pas trouvé
        """
        ingredient_clean_name_list = list(
            map(self.clean_ingredient_name, ingredient_name_list)
        )
        ingredient_to_match = ingredient_clean_name_list
        ingredient_matched = []

        logging.info(
            f"Matching: Looking for ingredients: {ingredient_to_match}."
        )

        if len(ingredient_to_match) > 0:
            # Build the WHERE conditions for each ingredient
            conditions = []
            for safe_ingredient in ingredient_to_match:
                condition = f"""(LOWER(ci."DESCRIP") LIKE '%{safe_ingredient.lower()}%'
                    OR LOWER(im."INGREDIENT_FROM_RECIPE_NAME") LIKE '%{safe_ingredient.lower()}%')"""
                conditions.append(condition)

            # Join conditions with OR
            where_clause = " OR ".join(conditions)

            query = f"""
            SELECT DISTINCT
                "DESCRIP",
                "PROTEIN_G",
                "SATURATED_FATS_G",
                "FAT_G",
                "CARB_G",
                "SODIUM_MG",
                "FIBER_G",
                "SUGAR_G",
                "ENERGY_KCAL",
                "INGREDIENT_FROM_RECIPE_NAME" as matched_ingredient
            FROM (
                SELECT
                    ci."DESCRIP",
                    ci."PROTEIN_G",
                    ci."SATURATED_FATS_G",
                    ci."FAT_G",
                    ci."CARB_G",
                    ci."SODIUM_MG",
                    ci."FIBER_G",
                    ci."SUGAR_G",
                    ci."ENERGY_KCAL",
                    ci."NDB_NO",
                    im."INGREDIENT_FROM_RECIPE_NAME"
                FROM {INGREDIENTS_NUTRIMENTS_TABLE_NAME} ci
                FULL OUTER JOIN {INGREDIENTS_MATCHED_TABLE_NAME} im
                    ON im."INGREDIENT_ID" = ci."NDB_NO"
                WHERE
                            {where_clause}
            ) AS result
            """

            result_sql = self.session.sql(query)
            result = parse_query_result(result_sql)
            logging.info(f"result: {result}")

            if result:
                for ingredient_key in ingredient_to_match:
                    # Prendre le meilleur match (correspondance exacte prioritaire)
                    best_match = None
                    exact_match = None

                    for row in result:
                        matched_ingredient = row["MATCHED_INGREDIENT"]
                        descrip = row["DESCRIP"]

                        # Utiliser safe_float pour toutes les conversions
                        nutrition_data = {
                            "name": descrip,
                            "matched_ingredient": matched_ingredient,
                            "protein": float(row["PROTEIN_G"]),
                            "saturated_fats": float(row["SATURATED_FATS_G"]),
                            "fat": float(row["FAT_G"]),
                            "carbs": float(row["CARB_G"]),
                            "sodium": float(row["SODIUM_MG"]),
                            "fiber": float(row["FIBER_G"]),
                            "sugar": float(row["SUGAR_G"]),
                            "calories": float(row["ENERGY_KCAL"]),
                        }
                        if matched_ingredient is not None:
                            # Correspondance exacte avec l'ingrédient matché
                            if matched_ingredient == ingredient_key:
                                exact_match = nutrition_data
                                break
                            # Meilleur match partiel
                            elif ingredient_key in matched_ingredient or any(
                                word in matched_ingredient
                                for word in ingredient_key.split()
                            ):
                                if best_match is None:
                                    best_match = nutrition_data

                    result_data = exact_match or best_match

                    if result_data:
                        # Mettre en cache
                        self.matched_ingredients_cache[ingredient_key] = (
                            result_data
                        )
                        ingredient_matched.append(result_data)
                    else:
                        # Pas trouvé - mettre en cache négatif
                        self.matched_ingredients_cache[ingredient_key] = None
                        ingredient_matched.append(None)
            else:
                logging.error(
                    "Failure: Getting matched ingredient query failed."
                )

        if None in ingredient_matched:
            logging.warning(
                "Failure: Some ingredients doesn't have matched ingredient."
            )
        return ingredient_matched

    def fetch_recipe_quantities(
        self, recipe_id: int
    ) -> Dict[str, Optional[float]]:
        """
        Returns list of (ingredient_string, qty_g_or_none) from INGREDIENTS_QUANTITY.
        Cached per recipe.
        """
        sdf = (
            self.session.table(INGREDIENTS_QUANTITY_TABLE_NAME)
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
            out[(ing or "").strip().lower()] = (
                float(qty) if qty is not None else None
            )

        return out

    def fetch_ingredients_nutrition(
        self, recipe_id: int, ingredients: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
         Returns mapping:
          key = LOWER(TRIM(ingredient_from_recipe_name))
          val = dict of nutrition columns per 100g (or None if not found)
        Cached per recipe+ingredient key.
        """
        keys = [(s or "").strip().lower() for s in ingredients]
        keys = [k for k in keys if k]
        missing = sorted(set(keys))
        if not missing:
            return {}

        im = self.session.table(INGREDIENTS_MATCHED_TABLE_NAME)
        ci = self.session.table(INGREDIENTS_NUTRIMENTS_TABLE_NAME)
        ", ".join("'" + k.replace("'", "''") + "'" for k in missing)

        ing_key_expr = lower(trim(col("INGREDIENT_FROM_RECIPE_NAME")))
        joined = (
            im.filter(col("RECIPE_ID") == int(recipe_id))
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
        w = Window.partition_by(col("ING_KEY")).order_by(
            col("SCORE_SANTE").desc_nulls_last()
        )
        ranked = joined.with_column("RN", row_number().over(w)).filter(
            col("RN") == 1
        )
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
        out: Dict[str, Optional[Dict[str, Any]]] = {k: None for k in missing}
        for r in rows:
            ing_key = r["ING_KEY"]
            vals = [r[c] for c in NUTRITION_COLS]
            out[ing_key] = dict(zip(NUTRITION_COLS, vals))
        return out

    def compute_recipe_nutrition_totals(
        self,
        recipe_id: int,
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
        ingredients_nutrition = self.fetch_ingredients_nutrition(
            recipe_id, ingredients
        )

        known_weight = 0.0
        unknown_count = 0

        for _, qty in ingredients_quantity.items():
            if qty is None:
                unknown_count += 1
            else:
                known_weight += float(qty)

        if unknown_count > 0:
            fill_qty = (
                max(total_weight - known_weight, 0.0) / unknown_count * 0.5
            )  # 0.5 to follow group 1 logic appended to db
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
            health_score=0.0,
        )
        for name, nutrition in ingredients_nutrition.items():
            if nutrition is None:
                continue
            quantity = ingredients_quantity.get(name)
            if quantity is None:
                quantity = fill_qty
            factor = float(quantity) / float(NUTRIENT_BASIS_GRAMS)

            recipe_nutrition.calories += (
                float(nutrition["ENERGY_KCAL"]) * factor
            )
            recipe_nutrition.protein_g += float(nutrition["PROTEIN_G"]) * factor
            recipe_nutrition.fat_g += float(nutrition["FAT_G"]) * factor
            recipe_nutrition.saturated_fats_g += (
                float(nutrition["SATURATED_FATS_G"]) * factor
            )
            recipe_nutrition.carb_g += float(nutrition["CARB_G"]) * factor
            recipe_nutrition.fiber_g += float(nutrition["FIBER_G"]) * factor
            recipe_nutrition.sugar_g += float(nutrition["SUGAR_G"]) * factor
            recipe_nutrition.sodium_mg += float(nutrition["SODIUM_MG"]) * factor

            recipe_nutrition.calcium_mg += (
                float(nutrition["CALCIUM_MG"]) * factor
            )
            recipe_nutrition.iron_mg += float(nutrition["IRON_MG"]) * factor
            recipe_nutrition.magnesium_mg += (
                float(nutrition["MAGNESIUM_MG"]) * factor
            )
            recipe_nutrition.potassium_mg += (
                float(nutrition["POTASSIUM_MG"]) * factor
            )
            recipe_nutrition.vitamin_c_mg += (
                float(nutrition["VITC_MG"]) * factor
            )
            recipe_nutrition.calcium_mg += (
                float(nutrition["CALCIUM_MG"]) * factor
            )
            recipe_nutrition.iron_mg += float(nutrition["IRON_MG"]) * factor
            recipe_nutrition.magnesium_mg += (
                float(nutrition["MAGNESIUM_MG"]) * factor
            )
            recipe_nutrition.potassium_mg += (
                float(nutrition["POTASSIUM_MG"]) * factor
            )
            recipe_nutrition.vitamin_c_mg += (
                float(nutrition["VITC_MG"]) * factor
            )

        return recipe_nutrition

    def scale_nutrition(
        self, n: NutritionDelta, factor: float
    ) -> NutritionDelta:
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
        fiber_ref = 30.0

        s_protein = min(protein_g / protein_ref, 1.0)
        s_fiber = min((fiber_g or 0.0) / fiber_ref, 1.0)

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

        h_sugar = subscore(sugar_g, sugar_limit, alpha_sugar)
        h_satfat = subscore(saturated_fats_g, satfat_limit, alpha_satfat)
        h_sodium = subscore(sodium_mg, sodium_limit, alpha_sodium)

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

        calcium_ref = 1000.0
        iron_ref = 18.0
        magnesium_ref = 350.0
        potassium_ref = 3500.0
        vitamin_c_ref = 90.0

        m_ca = min(max(calcium_mg, 0.0) / calcium_ref, 1.0)
        m_fe = min(max(iron_mg, 0.0) / iron_ref, 1.0)
        m_mg = min(max(magnesium_mg, 0.0) / magnesium_ref, 1.0)
        m_k = min(max(potassium_mg, 0.0) / potassium_ref, 1.0)
        m_c = min(max(vitamin_c_mg, 0.0) / vitamin_c_ref, 1.0)

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

        benefit = self.compute_benefit_score(
            protein_g=nutrition.protein_g, fiber_g=nutrition.fiber_g
        )
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
                    TransformService._pca_data_cache = (
                        self.load_pca_data_from_snowflake()
                    )
        self.pca_data = TransformService._pca_data_cache

    def load_pca_data(self):
        """Load PCA data from Snowflake with INGREDIENTS_TAGGED constraints or CSV as fallback"""
        if self.pca_data is None:
            try:
                # Tentative de chargement depuis Snowflake avec jointure INGREDIENTS_TAGGED
                if self.session is not None:
                    logging.info(
                        "Loading PCA data from Snowflake with constraints..."
                    )

                    query = f"""
                    SELECT
                        ic.NDB_NO,
                        ic.DESCRIP,
                        ic.ENERGY_KCAL,
                        ic.PROTEIN_G,
                        ic.SATURATED_FATS_G,
                        ic.FAT_G,
                        ic.CARB_G,
                        ic.SODIUM_MG,
                        ic.SUGAR_G,
                        ic.FIBER_G,
                        ic.CALCIUM_MG,
                        ic.IRON_MG,
                        ic.POTASSIUM_MG,
                        ic.VITC_MG,
                        ic.MAGNESIUM_MG,
                        ic.PCA_MACRO_1,
                        ic.PCA_MACRO_2,
                        ic.PCA_MACRO_3,
                        ic.PCA_MICRO_1,
                        ic.PCA_MICRO_2,
                        ic.CLUSTER_MACRO,
                        ic.CLUSTER_MICRO,
                        it.FOODON_LABEL,
                        COALESCE(it.IS_DAIRY, FALSE) AS IS_DAIRY,
                        COALESCE(it.IS_GLUTEN, FALSE) AS IS_GLUTEN,
                        COALESCE(it.CONTAINS_NUTS, FALSE) AS CONTAINS_NUTS,
                        COALESCE(it.IS_VEGETARIAN, FALSE) AS IS_VEGETARIAN,
                        COALESCE(it.IS_VEGETABLE, FALSE) AS IS_VEGETABLE
                    FROM {INGREDIENTS_CLUSTERING_TABLE_NAME} ic
                    LEFT JOIN {INGREDIENTS_TAGGED_TABLE_NAME} it
                        ON ic.NDB_NO = it.NDB_NO
                    """

                    result_cluster = self.session.sql(query)
                    result_data = parse_query_result(result_cluster)

                    if result_data:
                        df = pd.DataFrame(result_data)
                        for col in list(df.columns):
                            sample_row = df[col][0]
                            if isinstance(sample_row, (decimal.Decimal)):
                                df[col].apply(float)

                        # Renommer les colonnes pour correspondre au format attendu
                        self.pca_data = df.rename(
                            columns={
                                "NDB_NO": "NDB_No",
                                "DESCRIP": "Descrip",
                                "ENERGY_KCAL": "ENERGY_KCAL",
                                "PROTEIN_G": "PROTEIN_G",
                                "SATURATED_FATS_G": "SATURATED_FATS_G",
                                "FAT_G": "FAT_G",
                                "CARB_G": "CARB_G",
                                "SODIUM_MG": "SODIUM_MG",
                                "SUGAR_G": "SUGAR_G",
                                "FIBER_G": "FIBER_G",
                                "CALCIUM_MG": "CALCIUM_MG",
                                "IRON_MG": "IRON_MG",
                                "POTASSIUM_MG": "POTASSIUM_MG",
                                "VITC_MG": "VITC_MG",
                                "MAGNESIUM_MG": "MAGNESIUM_MG",
                                "PCA_MACRO_1": "PCA_macro_1",
                                "PCA_MACRO_2": "PCA_macro_2",
                                "PCA_MACRO_3": "PCA_macro_3",
                                "PCA_MICRO_1": "PCA_micro_1",
                                "PCA_MICRO_2": "PCA_micro_2",
                                "CLUSTER_MACRO": "Cluster_macro",
                                "CLUSTER_MICRO": "Cluster_micro",
                                "FOODON_LABEL": "FOODON_LABEL",
                                "IS_DAIRY": "is_lactose",
                                "IS_GLUTEN": "is_gluten",
                                "CONTAINS_NUTS": "contains_nuts",
                                "IS_VEGETARIAN": "is_vegetarian",
                                "IS_VEGETABLE": "is_vegetable",
                            }
                        )

                        # Convertir les booléens en entiers (0/1) pour compatibilité
                        constraint_columns = [
                            "is_lactose",
                            "is_gluten",
                            "contains_nuts",
                            "is_vegetarian",
                            "is_vegetable",
                        ]
                        for col in constraint_columns:
                            if col in self.pca_data.columns:
                                self.pca_data[col] = self.pca_data[col].apply(
                                    lambda x: 1 if x else 0
                                )

                        logging.info(
                            f"Success: PCA data loaded from Snowflake with constraints ({len(self.pca_data)} ingredients)"
                        )
                        return
                    else:
                        logging.warning(
                            "Warning: No data returned from Snowflake query, falling back to CSV"
                        )

                # Fallback: Charger le fichier CSV
                logging.info("Loading PCA data from CSV fallback...")
                csv_path = "ingredients_with_clusters.csv"
                df = pd.read_csv(csv_path)

                for col in list(df.columns):
                    sample_row = df[col][0]
                    if isinstance(sample_row, (decimal.Decimal)):
                        df[col].apply(float)

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
                        for word in [
                            "milk",
                            "cheese",
                            "butter",
                            "cream",
                            "yogurt",
                        ]
                    ):
                        self.pca_data.at[idx, "is_lactose"] = 1

                    # Détection gluten (céréales, pain, etc.)
                    if any(
                        word in descrip_lower
                        for word in [
                            "wheat",
                            "bread",
                            "flour",
                            "pasta",
                            "cereal",
                        ]
                    ):
                        self.pca_data.at[idx, "is_gluten"] = 1

                    # Détection noix
                    if any(
                        word in descrip_lower
                        for word in [
                            "nut",
                            "almond",
                            "peanut",
                            "walnut",
                            "pecan",
                        ]
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

                logging.info(
                    f"Success: PCA data loaded from CSV fallback ({len(self.pca_data)} ingredients)"
                )

            except Exception as e:
                logging.error(
                    f"Failure: PCA ingredients coordinates loading error. Error: {str(e)}. Traceback: {traceback.format_exc()}"
                )
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
            logging.warning(
                f"Failure:  Ingredient '{ingredient_name}' not found in PCA data"
            )
            return None

        # Take the first match
        row = matching_rows.iloc[0]
        logging.info(
            f"Success: Ingredient found: {ingredient_name} → {row['Descrip']}"
        )

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
        macro_cols = ["PCA_macro_1", "PCA_macro_2", "PCA_macro_3"]
        micro_cols = ["PCA_micro_1", "PCA_micro_2"]

        # Check that columns exist
        available_macro_cols = [
            col for col in macro_cols if col in df_filtered.columns
        ]
        available_micro_cols = [
            col for col in micro_cols if col in df_filtered.columns
        ]

        if not available_macro_cols and not available_micro_cols:
            logging.warning(
                "Failure:  No pca coordinates available in pca dataframe."
            )
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
        df_filtered = df_filtered[df_filtered["Descrip"] != row["Descrip"]]

        if df_filtered.empty:
            logging.warning(
                "Failure: No substitute found after applying constraints"
            )
            return None

        # Calculate global distances (macro + micro combination)
        df_filtered = df_filtered.copy()

        # Calculate macro distance
        if available_macro_cols:
            df_filtered["dist_macro"] = df_filtered[available_macro_cols].apply(
                lambda x: euclidean_distance(macro_vec, x.values), axis=1
            )
        else:
            df_filtered["dist_macro"] = 0

        # Calculate micro distance
        if available_micro_cols:
            df_filtered["dist_micro"] = df_filtered[available_micro_cols].apply(
                lambda x: euclidean_distance(micro_vec, x.values), axis=1
            )
        else:
            df_filtered["dist_micro"] = 0

        # Combined global score
        df_filtered["dist_macro"] = df_filtered["dist_macro"].astype(float)
        df_filtered["dist_micro"] = df_filtered["dist_micro"].astype(float)
        df_filtered["global_score"] = (
            macro_weight * df_filtered["dist_macro"]
            + micro_weight * df_filtered["dist_micro"]
        )

        # -------------------------
        # Filter similarities (not regex after all), 30/12/25
        # -------------------------
        main_word = ingredient_clean.split()[0]  # only the first word for now

        def filter_similar_df(df, k):
            filtered_rows = []
            for _, row_ in df.iterrows():
                name_lower = row_["Descrip"].lower()
                if not name_lower.startswith(main_word):
                    filtered_rows.append(row_)
                if len(filtered_rows) >= k:
                    break
            return pd.DataFrame(filtered_rows)

        # Sort by global score and take the top k
        best_substitutes = df_filtered.nsmallest(k, "global_score")
        # Filter ingredients with the same base name
        best_substitutes = filter_similar_df(best_substitutes, k)

        result = {"input_ingredient": row["Descrip"], "best_substitutes": []}

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

    def get_health_score(
        self,
        new_ingredients: List[str],
        recipe_id: int,
        serving_size: float,
        servings: float,
    ) -> NutritionDelta:
        """
        Calculates health score for a recipe based on give ingredients
        """
        new_recipe_nutrition = self.compute_recipe_nutrition_totals(
            recipe_id=recipe_id,
            ingredients=new_ingredients,
            serving_size=serving_size,
            servings=servings,
        )
        denom = (serving_size or 0) * (servings or 0)
        if denom > 0:
            scaled_nutrition = self.scale_nutrition(
                new_recipe_nutrition, factor=100.0 / denom
            )
        else:
            scaled_nutrition = new_recipe_nutrition  ## fallback servings null
        rhi_score = self.compute_rhi(scaled_nutrition)
        logging.info(f"Info: Computed RHI score: {rhi_score:.2f}")
        new_recipe_nutrition.health_score = rhi_score
        return new_recipe_nutrition

    def judge_substitute(
        self,
        candidates,
        recipe_ingredients: List[str],
        recipe_id: int,
        serving_size: float,
        servings: float,
    ) -> Tuple[str, NutritionDelta]:
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
                best_nutrition = self.get_health_score(
                    recipe_ingredients + [cand["name"]],
                    recipe_id,
                    serving_size,
                    servings,
                )
            else:
                candidat_nutrition = self.get_health_score(
                    recipe_ingredients + [cand["name"]],
                    recipe_id,
                    serving_size,
                    servings,
                )
                best_current_score = self.get_health_score(
                    recipe_ingredients + [best_ing["name"]],
                    recipe_id,
                    serving_size,
                    servings,
                )
                if (
                    candidat_nutrition.health_score
                    > best_current_score.health_score
                ):
                    best_ing = cand
                    best_nutrition = candidat_nutrition
        return best_ing, best_nutrition

    def substitute_ingr(
        self,
        ingredient: str,
        contraintes: TransformConstraints,
        recipe_ingredients: List[str],
        recipe_id: int,
        serving_size: float,
        servings: float,
    ) -> Tuple[str, bool, NutritionDelta]:
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
        substitute, nutrition = self.judge_substitute(
            candidates, recipe_ingredients, recipe_id, serving_size, servings
        )

        if substitute:
            substitute_name = substitute["name"]
            logging.info(
                f"Success: Found substitute for {ingredient} → {substitute_name} (PCA score: {substitute['global_score']:.3f})"
            )
            return substitute_name, True, nutrition

        return ingredient, False, self._zero_nutrition()

    def fetch_ingredients_tags(
        self, recipe_id: int, ingredients: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:

        if recipe_id not in self.recipe_tags_cache:
            self.recipe_tags_cache[recipe_id] = {}

        keys = [(s or "").strip().lower() for s in ingredients]
        keys = [k for k in keys if k]
        unique_keys = sorted(set(keys))

        missing = [k for k in unique_keys if k not in self.recipe_tags_cache[recipe_id]]
        if not missing:
            return self.recipe_tags_cache[recipe_id]

        for k in missing:
            self.recipe_tags_cache[recipe_id][k] = None

        im = self.session.table(INGREDIENTS_MATCHED_TABLE_NAME)
        ci = self.session.table(INGREDIENTS_NUTRIMENTS_TABLE_NAME)
        it = self.session.table(INGREDIENTS_TAGGED_TABLE_NAME)

        ing_key_expr = lower(trim(im["INGREDIENT_FROM_RECIPE_NAME"]))

        candidates = (
            im.filter(im["RECIPE_ID"] == int(recipe_id))
              .with_column("ING_KEY", ing_key_expr)
              .with_column("INGREDIENT_ID_NUM", im["INGREDIENT_ID"])
              .filter(col("ING_KEY").isin(missing))
              .filter(col("INGREDIENT_ID_NUM").is_not_null())
        )

        candidates_with_score = (
            candidates.join(ci, col("INGREDIENT_ID_NUM") == ci["NDB_NO"], how="left")
                      .select(
                          col("ING_KEY"),
                          col("INGREDIENT_ID_NUM").as_("INGREDIENT_ID"),
                          ci["SCORE_SANTE"].as_("SCORE_SANTE"),
                      )
        )

        w = Window.partition_by(col("ING_KEY")).order_by(
            col("SCORE_SANTE").desc_nulls_last(),
            col("INGREDIENT_ID").asc_nulls_last(),
        )

        best = (
            candidates_with_score.with_column("RN", row_number().over(w))
                                 .filter(col("RN") == 1)
                                 .select(col("ING_KEY"), col("INGREDIENT_ID"))
        )

        best_with_tags = (
            best.join(it, best["INGREDIENT_ID"] == it["NDB_NO"], how="left")
                .select(
                    best["ING_KEY"].as_("ING_KEY"),
                    best["INGREDIENT_ID"].as_("NDB_NO"),
                    it["DESCRIP"],
                    it["FOODON_LABEL"],
                    it["IS_DAIRY"],
                    it["IS_GLUTEN"],
                    it["CONTAINS_NUTS"],
                    it["IS_GRAIN"],
                    it["IS_SEAFOOD"],
                    it["IS_SWEETENER"],
                    it["IS_VEGETABLE"],
                    it["IS_VEGETARIAN"],
                )
        )

        rows = best_with_tags.collect()

        for r in rows:
            ing_key = r["ING_KEY"]
            if r["NDB_NO"] is None and r["DESCRIP"] is None and r["FOODON_LABEL"] is None:
                continue

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
        self, recipe: Recipe, constraints: TransformConstraints
    ) -> List[str]:
        """
        Single-pass ingredient loop:
          - Allergy/diet constraints -> immediate removal via tags (up to 3)
          - Reduction constraints -> compute contribution-based score and collect candidates
          - After loop: pick best candidates to fill remaining slots (no second loop over ingredients)
    
        Returns list of ingredient strings from recipe.ingredients.
        """
        try:
            allergy_constraints = ["no_lactose", "no_gluten", "no_nuts", "vegetarian", "vegan"]
            reduction_constraints = [
                "decrease_sugar", "decrease_sodium", "decrease_calories", "decrease_carbs",
                "increase_protein", "decrease_protein",
            ]
    
            active_allergy = any(getattr(constraints, c, False) for c in allergy_constraints)
            active_reduction = any(getattr(constraints, c, False) for c in reduction_constraints)
    
            if not active_allergy and not active_reduction:
                return []
    
            # Max removals rule
            max_items = 3 if active_allergy else (1 if active_reduction else 0)
            if max_items == 0:
                return []
    
            # Fetch only what we need
            ingredients_tags = {}
            ingredients_nutrition = {}
            qty_map = {}
    
            if active_allergy:
                logging.info("Allergy constraints active... Checking ingredient tags")
                ingredients_tags = self.fetch_ingredients_tags(recipe.id, recipe.ingredients)
    
            if active_reduction:
                logging.info("Reduction constraints active... Using nutrition + quantities for contribution scoring")
                ingredients_nutrition = self.fetch_ingredients_nutrition(recipe.id, recipe.ingredients)
                qty_map = self.fetch_recipe_quantities(recipe.id)
    
            def contrib(qty_g: float, per100: float) -> float:
                return qty_g * (per100 / 100.0)
    
            ingredients_to_remove: List[str] = []
            removed_set = set()
            candidates = []
    
            for ingredient in recipe.ingredients:
                if len(ingredients_to_remove) >= max_items:
                    break
                
                ing_key = (ingredient or "").strip().lower()
                if not ing_key:
                    continue
                
                should_remove = False
    
                # --- Allergy / diet checks (immediate removal) ---
                if active_allergy:
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
                            should_remove = True  # proxy
    
                if should_remove:
                    ingredients_to_remove.append(ingredient)
                    removed_set.add(ingredient)
                    continue
                
                # --- Reduction scoring (collect candidates) ---
                if active_reduction:
                    nutrition = ingredients_nutrition.get(ing_key)
                    qty = qty_map.get(ing_key)
    
                    if nutrition is None or qty is None:
                        continue
                    
                    try:
                        qty_g = float(qty)
                    except Exception:
                        continue
                    if qty_g <= 0:
                        continue
                    
                    score = 0.0
                    any_metric = False
    
                    if constraints.decrease_sugar:
                        score += contrib(qty_g, float(nutrition.get("SUGAR_G", 0.0) or 0.0))
                        any_metric = True
                    if constraints.decrease_sodium:
                        score += contrib(qty_g, float(nutrition.get("SODIUM_MG", 0.0) or 0.0))
                        any_metric = True
                    if constraints.decrease_calories:
                        score += contrib(qty_g, float(nutrition.get("ENERGY_KCAL", 0.0) or 0.0))
                        any_metric = True
                    if constraints.decrease_carbs:
                        score += contrib(qty_g, float(nutrition.get("CARB_G", 0.0) or 0.0))
                        any_metric = True
    
                    protein_c = contrib(qty_g, float(nutrition.get("PROTEIN_G", 0.0) or 0.0))
    
                    if constraints.decrease_protein:
                        score += protein_c
                        any_metric = True
    
                    if constraints.increase_protein:
                        # Prefer removing LOW protein contribution ingredients:
                        # subtract protein contribution so lower protein => higher score
                        score -= protein_c
                        any_metric = True
    
                    if any_metric:
                        candidates.append((score, ingredient))
    
            # Fill remaining slots from best reduction candidates
            remaining = max_items - len(ingredients_to_remove)
            if remaining > 0 and candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                for _, ing in candidates:
                    if len(ingredients_to_remove) >= max_items:
                        break
                    if ing in removed_set:
                        continue
                    ingredients_to_remove.append(ing)
                    removed_set.add(ing)
    
            return ingredients_to_remove[:3]
    
        except Exception as e:
            print(f" Error in identifying ingredients to remove: {e}")
            traceback.print_exc()
            return []

    def identify_ingredients_to_remove_by_llm(
        self, recipe: Recipe, constraints: TransformConstraints
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
            allergy_constraints = [
                "no_lactose",
                "no_gluten",
                "no_nuts",
                "vegetarian",
                "vegan",
            ]
            reduction_constraints = [
                "decrease_sugar",
                "decrease_sodium",
                "decrease_calories",
                "decrease_carbs",
                "increase_protein",
                "decrease_protein",
            ]

            active_allergy = [
                c for c in allergy_constraints if getattr(constraints, c, False)
            ]
            active_reduction = [
                c
                for c in reduction_constraints
                if getattr(constraints, c, False)
            ]

            if not active_allergy and not active_reduction:
                return []

            if active_allergy:
                ", ".join(active_allergy + active_reduction)
            else:
                ", ".join(active_reduction)
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
            Ingredients: {", ".join(recipe.ingredients)}
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
            cleaned_response = response_text.replace("\n", ",").replace(
                ";", ","
            )

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
                        if (
                            cleaned_item.lower() in recipe_ing.lower()
                            or recipe_ing.lower() in cleaned_item.lower()
                        ):
                            if recipe_ing not in ingredients_to_remove:
                                ingredients_to_remove.append(recipe_ing)
                            matched = True
                            break

                    if not matched:
                        print(
                            f"LLM: Ingredient '{cleaned_item}' not found in recipe"
                        )

                if len(ingredients_to_remove) >= 3:
                    break
            return ingredients_to_remove

        except Exception as e:
            print(f"LLM error for ingredient identification: {e}")
            traceback.print_exc()
            return []

    def _map_add_constraint_to_nutrient(self, constraint_name: str) -> Optional[str]:
        """
        Maps an ADD constraint to the corresponding nutrient column.
        Returns None if the constraint is not supported.
        """
        return ADD_CONSTRAINT_TO_NUTRIENT.get(constraint_name)

    def _get_active_add_constraint(self, constraints):
        for c in [
            "increase_protein",
            "decrease_protein",
            "increase_fiber",
            "decrease_sugar",
            "decrease_carbs",
            "decrease_calories",
            "decrease_sodium",
            "decrease_satfat",
        ]:
            if getattr(constraints, c, False):
                return c
        return None

    def _infer_role_from_tags(self, tags: Dict[str, Any]) -> str:
        """
        Infer the dominant culinary/nutritional role of an ingredient
        based on available tagging information.

        Roles are used ONLY to avoid redundancy when ADDing ingredients.
        """

        if not tags:
            return "other"

        if tags.get("IS_SEAFOOD"):
            return "animal_protein"
        if tags.get("IS_VEGETARIAN") is False:
            return "animal_protein"

        if tags.get("IS_SWEETENER"):
            return "sugar"

        if tags.get("IS_GRAIN"):
            return "carb"

        if tags.get("IS_DAIRY"):
            return "dairy_fat"

        if tags.get("IS_VEGETABLE"):
            return "plant"

        if tags.get("CONTAINS_NUTS"):
            return "nuts"

        return "other"
     
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
                if (
                    step_cleaned[0].isdigit()
                    or step_cleaned.startswith("-")
                    or step_cleaned.startswith("*")
                ):  # Clean list formats
                    cleaned_step = step_cleaned.lstrip(
                        "0123456789.-*) "
                    ).strip()
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
            logging.error(
                f"Failure:  Error found with recipe adaptation steps with substitution transformation made by LLM. Error: {str(e)}. Traceback: {traceback.format_exc()}"
            )
            # Fallback: simple manual adaptation
            adapted_steps = recipe.steps
            adapted_steps = [
                step.replace(original, substitute)
                for original, substitute in substitutions.items()
                for step in adapted_steps
            ]
            return adapted_steps, []

    def adapt_recipe_delete(
        self, recipe: Recipe, ingredients_to_delete: List[str]
    ) -> Tuple[List[str], List[str]]:
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

                if (
                    step_cleaned[0].isdigit()
                    or step_cleaned.startswith("-")
                    or step_cleaned.startswith("*")
                ):  # Clean list formats
                    cleaned_step = step_cleaned.lstrip(
                        "0123456789.-*) "
                    ).strip()
                    if cleaned_step:
                        new_steps.append(cleaned_step)
                elif step_cleaned.lower().startswith("note"):
                    # Extract the note after "Note:"
                    note_content = step_cleaned.split(":", 1)[-1].strip()
                    if note_content:
                        notes.append(note_content)

            # Validation: if no steps were extracted, fallback to original steps
            if not new_steps:
                print(
                    "LLM: No valid steps extracted, using original steps -> adapt_recipe_delete"
                )
                return recipe.steps, notes

            print(f"LLM: {len(new_steps)} adapted steps, {len(notes)} notes")
            return new_steps, notes

        except Exception as e:
            logging.error(
                f"Failure:  Error found with recipe adaptation steps for deletion transformation made by LLM. Error: {str(e)}. Traceback: {traceback.format_exc()}"
            )

            # Fallback: naive removal of ingredient words in steps
            adapted_steps = list(recipe.steps)
            for ing in ingredients_to_delete:
                adapted_steps = [
                    step.replace(ing, "").strip() for step in adapted_steps
                ]

            return adapted_steps, []

    def adapt_recipe_add_with_llm(self,recipe: Recipe,added_ingredient: List[str]) -> Tuple[List[str], List[str]]:
        """
        Adapt recipe steps after ADD transformation using LLM.
        Returns: (new_steps, notes)
        """

        base_prompt = f"""
        You are an expert chef specializing in recipe enrichment.
    
        ORIGINAL RECIPE:
        Name: {recipe.name}
        Ingredients: {recipe.ingredients}
        Steps:
        {chr(10).join(recipe.steps)}
    
        INGREDIENT TO ADD:
        - {added_ingredient}
    
        YOUR TASK:
        Adapt the recipe steps to INCORPORATE the new ingredient(s) while maintaining the dish's balance and identity.
    
        GUIDELINES:
        1. Add the ingredient(s) only where it makes culinary sense
        2. Modify existing steps when possible instead of adding many new ones
        3. If necessary, add ONE new step per ingredient at the most appropriate moment
        4. Preserve the original order and numbering of steps
        5. Do NOT remove existing ingredients or steps
        6. Do NOT introduce additional ingredients
        7. Keep instructions concise and realistic
    
        OUTPUT FORMAT:
        - Return the adapted recipe steps in numbered format
        - Optionally add notes starting with "Note:"
    
        ADAPTED RECIPE STEPS:
        """

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

            if not response_text:
                return recipe.steps, []

            parsed_steps = response_text.split("\n")

            new_steps: List[str] = []
            notes: List[str] = []

            for step in parsed_steps:
                step_cleaned = step.strip()
                if not step_cleaned:
                    continue

                if step_cleaned[0].isdigit() or step_cleaned.startswith(("-", "*")):
                    cleaned_step = step_cleaned.lstrip("0123456789.-*) ").strip()
                    if cleaned_step:
                        new_steps.append(cleaned_step)
                elif step_cleaned.lower().startswith("note"):
                    notes.append(step_cleaned.split(":", 1)[-1].strip())

            if not new_steps:
                return recipe.steps, notes

            return new_steps, notes

        except Exception as e:
            logging.error(
                f"Failure: ADD recipe adaptation via LLM failed. Error: {str(e)}"
            )
            # Fallback: simple append
            fallback_steps = recipe.steps + [
                f"Add {added_ingredient}."
            ]
            return fallback_steps, []

    def fetch_tags_for_ndb_nos(self, ndb_nos: List[str]) -> Dict[str, Dict[str, Any]]:
        if not ndb_nos:
            return {}

        it = self.session.table(INGREDIENTS_TAGGED_TABLE_NAME)
        cleaned = [str(x).strip() for x in ndb_nos if x is not None and str(x).strip()]

        rows = (
            it.filter(col("NDB_NO").isin( cleaned))
              .select(
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
              .collect()
        )

        out: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            ndb = r["NDB_NO"]
            if ndb is None:
                continue
            out[ndb] = {
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
        return out


    def transform(
        self,
        recipe: Recipe,
        ingredients_to_remove: List[str],
        ingredients_to_add: List[str],
        constraints: TransformConstraints,
    ) -> TransformResponse:
        """
        Transform a recipe based on constraints and ingredients to remove, full pipeline
        """
        log_msg = "Start(Transform Service): Call transform service."
        logging.info(log_msg)
        self.log_msg.append(log_msg)

        success = True

        try:
            notes = []
            ingredients_to_transform: List[str] = []

            # Step 1: Find ingredient to 'transform' depending on constraints if not received
            transformation_type = constraints.transformation

            log_msg = "Start(Step 1): Check ingredients to modify."
            logging.info(log_msg)
            self.log_msg.append(log_msg)
            allergy_constraints = ["no_lactose", "no_gluten", "no_nuts", "vegetarian", "vegan"]
            active_allergy = any(getattr(constraints, c, False) for c in allergy_constraints)
            
            if transformation_type != TransformationType.ADD:

                if ingredients_to_remove:
                    logging.info("Recipe has defined ingredients to remove")
                    ingredients_to_transform = ingredients_to_remove
                    if active_allergy:
                        logging.info("Allergy Constraints active... Verifying ingredient tags")
                        extra_ingr = self.identify_ingredients_to_remove_by_algo(recipe, constraints)
                        if not extra_ingr:
                            logging.info("Defaulting to LLM identification for allergy constraints")
                            extra_ingr = self.identify_ingredients_to_remove_by_llm(recipe, constraints)
                        if extra_ingr:
                            for ingr in extra_ingr:
                                if ingr not in ingredients_to_transform:
                                    ingredients_to_transform.append(ingr)
                else:
                    # Algorithm in priority to identify ingredients
                    log_msg = "Running(Step 1): Identify ingredient to remove by algorithm."
                    logging.info(log_msg)
                    self.log_msg.append(log_msg)

                    ingredients_to_transform = (
                        self.identify_ingredients_to_remove_by_algo(
                            recipe, constraints
                        )
                    )

                    # LLM fallback if the algorithm finds nothing
                    if not ingredients_to_transform:
                        log_msg = "Running(Step 1): Identify ingredients with algo failed, fallback with llm."
                        logging.info(log_msg)
                        self.log_msg.append(log_msg)

                        print("Step 1b: LLM fallback for identification...")
                        ingredients_to_transform = (
                            self.identify_ingredients_to_remove_by_llm(
                                recipe, constraints
                            )
                        )

                    if not ingredients_to_transform:
                        log_msg = "Error(Step 1): No ingredient to modify found."
                        logging.error(log_msg)
                        self.log_msg.append(log_msg)
                        raise Exception
                    else:
                        log_msg = f"Running(Step 1): Ingredients identified: {ingredients_to_transform}."
                        logging.info(log_msg)
                        self.log_msg.append(log_msg)

                log_msg = "End(Step 1): finished (Identify ingredients to remove."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

            if not ingredients_to_transform:
                ingredients_to_transform = []
            if not ingredients_to_add:
                ingredients_to_add = []
                
            # Input for whole pipeline
            transformations = {}
            transformation_count = 0
            new_recipe_score = 0.0
            # Ingredients to keep from original recipe
            base_ingredients = [
                ing
                for ing in recipe.ingredients
                if ing not in ingredients_to_transform
            ]

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
            new_recipe_nutrition = self._zero_nutrition()

            # Pipeline diversion based on transformation type
            if transformation_type == TransformationType.SUBSTITUTION:
                log_msg = "Starting(Step 2): Transformation of type substitution recognized, starting process..."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                log_msg = "Running(Step 2): Load clustering coordinates and tag of each ingredients."
                logging.info(log_msg)
                self.log_msg.append(log_msg)
                # Step 2 : Find substitutes for ingredients to transform, function returns new recipe health score as well.
                if self.pca_data is None:
                    self.load_pca_data()

                log_msg = "Running(Step 2): Ged matching ingredient name between recipe and ingredients nutriment databse."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                # Use cache match when available, otherwise query the database to get matched ingredient
                ingredients_to_substitute_matched = [
                    ing_dict.get("name")
                    for ing_dict in self.get_ingredient_matched(
                        ingredients_to_transform
                    )
                ]

                ingredients_user_candidates =[
                        ing_dict.get("name")
                        for ing_dict in self.get_ingredient_matched(
                            ingredients_to_add
                        )
                    ]

                log_msg = (
                    "Running(Step 2): Ingredients matched found"
                    + f"\nMatched ingredients {ingredients_to_substitute_matched}, {type(ingredients_to_substitute_matched)}"
                    + f"\nRequest ingredients changes not needed {base_ingredients}, {type(base_ingredients)}"
                    + f"\nIngredients to transform {ingredients_to_transform}, {type(ingredients_to_transform)}."
                )
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                log_msg = "Running(Step 2): Looking for ingredients to replace candidates."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                working_ingredients = list(base_ingredients)
                for original_ing, matched_name, user_candidate, matched_name_candidate in zip(
                    ingredients_to_transform, ingredients_to_substitute_matched,
                    ingredients_to_add, ingredients_user_candidates
                ):
                    log_msg = "Running(Step 2): Looking for ({original_ing} matched with {matched_name}) substitute candidat."
                    logging.info(log_msg)
                    self.log_msg.append(log_msg)

                    substitute, was_substituted, new_recipe_nutrition = (
                        self.substitute_ingr(
                            matched_name,
                            constraints,
                            working_ingredients,
                            recipe.id,
                            recipe.serving_size,
                            recipe.servings,
                        )
                    )

                    if was_substituted:
                        log_msg = (
                            "Running(Step 2): Found substitute {substitute} with nutrition {new_recipe_nutrition}."
                            + "Updating the new_recipe (ingredients and health score)."
                        )
                        logging.info(log_msg)
                        self.log_msg.append(log_msg)

                        transformations[original_ing] = substitute
                        transformation_count += 1

                        # Update the working ingredient list for the next iteration
                        # (replace original_ing if it still exists, otherwise just append substitute)
                        if original_ing in working_ingredients:
                            working_ingredients = [
                                substitute if x == original_ing else x
                                for x in working_ingredients
                            ]
                        else:
                            working_ingredients.append(substitute)

                        # Apply substitutions to the full recipe ingredient list
                        new_ingredients = [
                            transformations.get(ingredient, ingredient)
                            for ingredient in recipe.ingredients
                        ]
                        new_recipe.ingredients = new_ingredients

                        # Trust the nutrition returned by the last substitute_ingr call (now based on updated working_ingredients)
                        new_recipe_score = new_recipe_nutrition.health_score
                        new_recipe.health_score = new_recipe_score

                log_msg = "End(Step 2): Step 2 finished for Substitution (Subtitute ingredients found for eache ingredients to remove)."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                log_msg = "Start(Step 3): Adapting new recipes steps with llm."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                # Step 3 : Adapt recipe step with LLM
                if transformations:
                    new_recipe.steps, notes = self.adapt_recipe_with_llm(
                        new_recipe, transformations
                    )
                logging.info(
                    "Success: Step 3 finished for Substitution (LLM's adapted new_recipe steps successfully)."
                )

            elif transformation_type == TransformationType.ADD:
                added_ingredient = []
                # Identifier la contrainte ADD active
                active_constraint = self._get_active_add_constraint(constraints)
                if (not active_constraint and len(ingredients_to_add)<=0):
                    notes.append("No ADD constraint provided.")
                    new_recipe_nutrition = self._zero_nutrition()
                    new_recipe.health_score = recipe.health_score
                
                if (len(ingredients_to_add)>0):
                    added_ingredient.extend(ingredients_to_add)
                if active_constraint:
                    # Nutriment cible à optimiser
                    target_nutrient = self._map_add_constraint_to_nutrient(active_constraint)
                    if not target_nutrient: #pas de contrainte qui permet l'ajout
                        notes.append(f"Unsupported ADD constraint: {active_constraint}")
                        new_recipe_nutrition = self._zero_nutrition()
                        new_recipe.health_score = recipe.health_score

                    else:
                        # 4 Déterminer les rôles nutritionnels déjà présents
                        recipe_tags = self.fetch_ingredients_tags(recipe.id, recipe.ingredients)
                        existing_roles = set()
                        for ing in recipe.ingredients:
                            tags = recipe_tags.get((ing or "").strip().lower())
                            role = self._infer_role_from_tags(tags)
                            existing_roles.add(role)

                        # 5 Load PCA catalog (ingredients + nutrients)
                        if self.pca_data is None:
                            self.load_pca_data()
                        df = self.pca_data.copy()

                        # 7 Nutrient-guided filtering (ONLY if the nutrient column exists)
                        if target_nutrient not in df.columns:
                            notes.append(f"Missing nutrient column in pca_data: {target_nutrient}")
                            df_filtered = df
                        else:
                            median_value = df[target_nutrient].median()
                            if active_constraint.startswith("increase"):
                                df_filtered = df[df[target_nutrient] > median_value].sort_values(target_nutrient, ascending=False)
                            else:
                                df_filtered = df[df[target_nutrient] < median_value].sort_values(target_nutrient, ascending=True)

                        # Build a pool of potential candidates with IDs
                        df_filtered = df_filtered.dropna(subset=["Descrip", "NDB_No"])
                        pool = df_filtered[["NDB_No", "Descrip"]].head(200).to_dict("records")

                        # Fetch tags by NDB_NO (you implement this)
                        tags_map = self.fetch_tags_for_ndb_nos([p["NDB_No"] for p in pool])

                        candidates = []
                        seen = set()

                        for p in pool:
                            ndb = int(p["NDB_No"])
                            name = str(p["Descrip"]).strip()
                            key = name.lower()

                            if not name or key in seen:
                                continue
                            seen.add(key)

                            tags = tags_map.get(ndb) or {}

                            # diet constraints (match your schema!)
                            if constraints.no_lactose and tags.get("IS_DAIRY") is True:
                                continue
                            if constraints.no_gluten and tags.get("IS_GLUTEN") is True:
                                continue
                            if constraints.no_nuts and tags.get("CONTAINS_NUTS") is True:
                                continue
                            if constraints.vegetarian and tags.get("IS_VEGETARIAN") is False:
                                continue
                            if constraints.vegan and tags.get("IS_VEGETABLE") is False:  # proxy
                                continue

                            role = self._infer_role_from_tags(tags)

                            # optional: ignore "other" so you don't block everything
                            if role != "other" and role in existing_roles:
                                continue
                            
                            candidates.append({"name": name})

                            if len(candidates) >= 5:
                                break

                        # 9 Sélection finale par gain marginal de RHI
                        best_ing, best_nutrition = self.judge_substitute(
                            candidates,
                            recipe.ingredients,
                            recipe.id,
                            recipe.serving_size,
                            recipe.servings
                        )

                        if best_ing:
                            added_ingredient.append(best_ing["name"])
                            new_recipe.name = f"{recipe.name} with {added_ingredient}"
                        else:
                            notes.append("No suitable ingredient found to add.")
                
                if added_ingredient:
                    seen = set()
                    added_ingredient = [
                        x for x in added_ingredient
                        if (x not in seen and not seen.add(x)) and (x not in recipe.ingredients)
                    ]

                    new_recipe.ingredients = recipe.ingredients + added_ingredient
                    recipe_health = self.get_health_score(
                        new_recipe.ingredients,
                        recipe.id,
                        recipe.serving_size,
                        recipe.servings
                    )
                    best_nutrition = recipe_health
                    new_steps, add_notes = self.adapt_recipe_add_with_llm(
                                recipe=new_recipe,
                                added_ingredient=added_ingredient)
                    new_recipe.steps = new_steps
                    notes.extend(add_notes)
                    new_recipe_nutrition = best_nutrition
                    new_recipe.health_score = best_nutrition.health_score
                    notes.append(f"Added ingredient: {added_ingredient}")

            elif (
                transformation_type == TransformationType.DELETE
                and ingredients_to_transform
            ):
                log_msg = "Start(Step 2): Transformation Delete ingredient recognized, starting process."
                logging.info(log_msg)
                self.log_msg.append(log_msg)
                # Step 2 : Delete ingredients from recipe, calculate health score after deletion
                new_recipe_nutrition = self.compute_recipe_nutrition_totals(
                    recipe_id=recipe.id,
                    ingredients=base_ingredients,
                    serving_size=recipe.serving_size,
                    servings=recipe.servings,
                )
                denom = (recipe.serving_size or 0) * (recipe.servings or 0)
                if denom > 0:
                    scaled_nutrition = self.scale_nutrition(
                        new_recipe_nutrition, factor=100.0 / denom
                    )
                else:
                    scaled_nutrition = (
                        new_recipe_nutrition  ## fallback servings null
                    )
                new_recipe_score = self.compute_rhi(scaled_nutrition)
                new_recipe_nutrition.health_score = new_recipe_score
                new_recipe.health_score = new_recipe_score
                log_msg = "End(Step 2): finished for Deletion (Removed successfully unwanted ingredients and computed new health score)."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                # Step 3 : Adapt recipe step with LLM
                log_msg = "Start(Step 3): Adapting new recipes steps with llm."
                logging.info(log_msg)
                self.log_msg.append(log_msg)

                new_recipe.steps, notes = self.adapt_recipe_delete(
                    recipe, ingredients_to_transform
                )

                log_msg = (
                    "End(Step 3): Adapting recipe's steps ended successfully."
                )
                logging.info(log_msg)
                self.log_msg.append(log_msg)

            # Step 3 : Adapt recipe step with LLM
            log_msg = "Start(Step 4): Compute health score for new recipe."
            logging.info(log_msg)
            self.log_msg.append(log_msg)

            # Step 4 : Build output
            original_nutrition = self.compute_recipe_nutrition_totals(
                recipe_id=recipe.id,
                ingredients=recipe.ingredients,
                serving_size=recipe.serving_size,
                servings=recipe.servings,
            )
            original_nutrition.health_score = recipe.health_score

            log_msg = "End(Step 4): New score computation successfully ended."
            logging.info(log_msg)
            self.log_msg.append(log_msg)

            response = TransformResponse(
                recipe=new_recipe,
                original_name=recipe.name,
                transformed_name=new_recipe.name,
                substitutions=None,
                nutrition_before=original_nutrition,
                nutrition_after=new_recipe_nutrition,
                success=success,
                message="\n".join(self.log_msg + notes),
            )

            log_msg = "End(TransformService): Transform service output sucessfully built, returning response."
            logging.info(log_msg)
            self.log_msg.append(log_msg)
            return response

        except Exception as e:
            log_msg = f"Failure: Transform function failed. Error: {str(e)}. Traceback: {traceback.format_exc()}\nReturning default response with input recipe."
            logging.error(log_msg)
            self.log_msg.append(log_msg)

            success = False
            response = TransformResponse(
                recipe=recipe,
                original_name=recipe.name,
                transformed_name=recipe.name,
                substitutions=None,
                nutrition_before=None,
                nutrition_after=None,
                success=success,
                message="\n".join(self.log_msg),
            )

            return response


def transform_recipe(session: Session, request: str) -> str:
    """
    Transform endpoint handler - Snowflake Procedure

    Args:
        session: Snowflake session to execute queries
        request: JSON string with TransformRequest structure

    Returns:
        JSON string with TransformResponse structure
    """

    # Input loading
    try:
        loaded_request: dict = json.loads(request)
        input_recipe: Recipe = Recipe(**loaded_request["recipe"])
        input_ingredients_to_remove: List[str] = loaded_request.get(
            "ingredients_to_remove"
        )
        input_ingredients_to_add: List[str] = loaded_request.get(
            "ingredients_to_add"
        )
        input_constraints: TransformConstraints = TransformConstraints(
            **loaded_request.get("constraints", {})
        )
    except Exception as e:
        return f"Transform Service:\nError in parsing request: {e}\nTraceback : {traceback.format_exc()}"

    service = TransformService(session)
    # Call transform service

    output = service.transform(
        input_recipe, input_ingredients_to_remove, input_ingredients_to_add, input_constraints
    )

    try: 
        log_msg = "\nLog transformation: Calling procedure to log transformation recipe."
        logging.info(log_msg)
        output.message += log_msg

        output_fmt = to_dict(output)
        session.call(
            LOG_RECIPE_TABLE_NAME,
            '', # CONVERSATION_ID
            '', # USER_ID
            output_fmt,           # FULL_RESPONSE
            to_dict(input_recipe)   # ORIGINAL_RECIPE
        )
        return format_output(output_fmt)
    except Exception as e:
        log_msg = f"\nLog transformation: Error in logging recipe transformation.\nError: {e}\nTraceback : {traceback.format_exc()}"
        logging.error(log_msg)
        output.message += log_msg
        output_fmt = format_output(to_dict(output))

        
    return output_fmt
