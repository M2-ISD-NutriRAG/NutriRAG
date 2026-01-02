################################################################################################################

#                                        Transform service interface

################################################################################################################
import json
from enum import Enum
from typing import Optional, List, Dict, Any
from snowflake.snowpark import Session
import traceback
import pandas as pd
import numpy as np
from math import ceil


class TransformationType(Enum):
    ADD = 0
    DELETE = 1
    SUBSTITUTION = 2


class TransformConstraints:
    # Constraints for recipe transformation
    def __init__(
        self,
        transformation: TransformationType,
        no_lactose: Optional[bool] = False,
        no_gluten: Optional[bool] = False,
        no_nuts: Optional[bool] = False,
        vegetarian: Optional[bool] = False,
        vegan: Optional[bool] = False,
        increase_protein: Optional[bool] = False,
        decrease_sugar: Optional[bool] = False,
        decrease_protein: Optional[bool] = False,
        decrease_carbs: Optional[bool] = False,
        decrease_calories: Optional[bool] = False,
        decrease_sodium: Optional[bool] = False,
    ):
        self.transformation = transformation
        self.no_lactose = no_lactose
        self.no_gluten = no_gluten
        self.no_nuts = no_nuts
        self.vegetarian = vegetarian
        self.vegan = vegan
        self.increase_protein = increase_protein
        self.decrease_sugar = decrease_sugar
        self.decrease_protein = decrease_protein
        self.decrease_carbs = decrease_carbs
        self.decrease_calories = decrease_calories
        self.decrease_sodium = decrease_sodium


class Recipe:
    def __init__(
        self,
        name: str,
        ingredients: List[str],
        quantity_ingredients: List[str],
        minutes: float,
        steps: List[str],
    ):
        self.name = name
        self.ingredients = ingredients
        self.quantity_ingredients = quantity_ingredients
        self.minutes = minutes
        self.steps = steps


class TransformRequest:
    # Transform request body
    def __init__(
        self,
        recipe: Recipe,
        ingredients_to_remove: Optional[List[str]] = None,
        constraints: Optional[TransformConstraints] = None,
    ):
        self.recipe = recipe
        self.ingredients_to_remove = ingredients_to_remove
        self.constraints = constraints


class Substitution:
    # Single ingredient substitution
    def __init__(
        self,
        original_ingredient: str,
        substitute_ingredient: str,
        original_quantity: Optional[float] = None,
        substitute_quantity: Optional[float] = None,
        reason: str = "",
    ):
        self.original_ingredient = original_ingredient
        self.substitute_ingredient = substitute_ingredient
        self.original_quantity = original_quantity
        self.substitute_quantity = substitute_quantity
        self.reason = reason


class NutritionDelta:
    # Changes in nutrition values
    def __init__(
        self,
        calories: float = 0.0,
        protein_g: float = 0.0,
        saturated_fats_g: float = 0.0,
        fat_g: float = 0.0,
        carb_g: float = 0.0,
        fiber_g: float = 0.0,
        sodium_mg: float = 0.0,
        sugar_g: float = 0.0,
        score_health: float = 0.0,
    ):
        self.calories = calories
        self.protein_g = protein_g
        self.saturated_fats_g = saturated_fats_g
        self.fat_g = fat_g
        self.carb_g = carb_g
        self.fiber_g = fiber_g
        self.sodium_mg = sodium_mg
        self.sugar_g = sugar_g
        self.score_health = score_health


class TransformResponse:
    # Transform response
    def __init__(
        self,
        recipe: Recipe,
        original_name: str,
        transformed_name: str,
        substitutions: Optional[List[Substitution]] = None,
        nutrition_before: Optional[NutritionDelta] = None,
        nutrition_after: Optional[NutritionDelta] = None,
        success: bool = True,
        message: Optional[str] = None,
    ):
        self.recipe = recipe
        self.original_name = original_name
        self.transformed_name = transformed_name
        self.substitutions = substitutions
        self.nutrition_before = nutrition_before
        self.nutrition_after = nutrition_after
        self.success = success
        self.message = message


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


NUTRIENT_GRAMS = 100


class TransformService:
    # async nécessaire pour le constructeur ?
    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.ingredients_cache: Dict[str, Optional[Dict]] = {}
        self.pca_data = None  # Coordonnées des ingrédients pour clustering
        self._load_pca_data()

    def _get_ingredient_nutrition(self, ingredient_name: str) -> Optional[Dict]:
        """
        Récupère les informations nutritionnelles d'un seul ingrédient depuis la base

        Args:
            ingredient_name: Nom de l'ingrédient à chercher

        Returns:
            Dict avec les infos nutritionnelles ou None si pas trouvé
        """
        ingredient_key = ingredient_name.lower().strip()
        if ingredient_key in self.ingredients_cache:
            return self.ingredients_cache[ingredient_key]

        try:
            # NOUVELLE STRUCTURE: Utiliser la table de liaison INGREDIENTS_MATCHING
            # pour trouver NDB_NO puis chercher dans CLEANED_INGREDIENTS
            safe_ingredient = ingredient_name.replace("'", "''")

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
                    FROM NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS ci
                    FULL OUTER JOIN NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING im
                        ON im."INGREDIENT_ID" = ci."NDB_NO"
                    WHERE
                        LOWER(ci."DESCRIP") LIKE '%{safe_ingredient.lower()}%'
                        OR LOWER(im."INGREDIENT_FROM_RECIPE_NAME") LIKE '%{safe_ingredient.lower()}%'
                ) AS result
            """

            result_sql = self.session.sql(query)
            result = parse_query_result(result_sql)

            if result:
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
                    self.ingredients_cache[ingredient_key] = result_data
                    print(
                        f" Ingrédient trouvé: {ingredient_name} → {result_data['name']}"
                    )
                    return result_data

            # Pas trouvé - mettre en cache négatif
            self.ingredients_cache[ingredient_key] = None
            print(f"⚠️ Ingrédient non trouvé dans la base: {ingredient_name}")
            return None

        except Exception as e:
            print(
                f"❌_get_ingredient : Erreur recherche ingrédient '{ingredient_name}': {e}"
            )
            return None

    def calculate_health_score(self, total_nutrition: NutritionDelta) -> float:
        """Calcule le score santé selon la formule donnée"""
        score = (
            100
            - (total_nutrition.calories / 50)
            - (total_nutrition.saturated_fats_g * 2)
            - (total_nutrition.fat_g * 2)
            - (total_nutrition.sodium_mg / 100)
            - (total_nutrition.sugar_g * 1)
            + (total_nutrition.protein_g * 1.5)
            + (total_nutrition.fiber_g * 1.2)
            + (total_nutrition.carb_g * 1.1)
        )
        return score

    def calculer_nutrition_recette(
        self, ingredient_list: List[str], ingredient_quantity: List[str]
    ) -> NutritionDelta:
        """Calcule la nutrition totale de la recette"""

        total_nutrition = NutritionDelta()
        for ingredient, qty in zip(ingredient_list, ingredient_quantity):
            qty = int(qty)  # A changer si multi type
            ingredient_data = self._get_ingredient_nutrition(ingredient)

            if ingredient_data:
                # S'assurer que toutes les valeurs sont des float avant les calculs
                calories = ceil(ingredient_data["calories"] / NUTRIENT_GRAMS)
                protein = ceil(ingredient_data["protein"] / NUTRIENT_GRAMS)
                saturated_fat = ceil(
                    ingredient_data["saturated_fats"] / NUTRIENT_GRAMS
                )
                fat = ceil(ingredient_data["fat"] / NUTRIENT_GRAMS)
                carbs = ceil(ingredient_data["carbs"] / NUTRIENT_GRAMS)
                fiber = ceil(ingredient_data["fiber"] / NUTRIENT_GRAMS)
                sodium = ceil(ingredient_data["sodium"] / NUTRIENT_GRAMS)
                sugar = ceil(ingredient_data["sugar"] / NUTRIENT_GRAMS)

                total_nutrition.calories += calories
                total_nutrition.protein_g += protein * qty
                total_nutrition.fat_g += fat * qty
                total_nutrition.saturated_fats_g += saturated_fat * qty
                total_nutrition.sugar_g += sugar * qty
                total_nutrition.sodium_mg += sodium * qty
                total_nutrition.carb_g += carbs * qty
                total_nutrition.fiber_g += fiber * qty

        total_nutrition.score_health = self.calculate_health_score(
            total_nutrition
        )
        return total_nutrition

    def _load_pca_data(self):
        """Charge les données PCA depuis Snowflake ou CSV en fallback"""
        try:
            print(" Chargement des données PCA depuis Snowflake...")

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

            print(
                f"[1.4-_load_pca_data] ✅ Données CSV chargées: {len(self.pca_data)} ingrédients"
            )

        except Exception as e:
            print(f"[1.5-_load_pca_data] ❌ Erreur chargement CSV: {e}")
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
        Trouve les k meilleurs substituts d'un ingrédient selon PCA macro/micro

        Args:
            ingredient_name: Nom de l'ingrédient à substituer
            constraints: Contraintes de transformation
            micro_weight: Poids des micronutriments
            macro_weight: Poids des macronutriments
            k: Nombre de substituts à retourner

        Returns:
            Dict avec les meilleurs substituts
        """
        if self.pca_data is None:
            print("❌ Données PCA non disponibles")
            return None

        # Nettoyer le nom de l'ingrédient
        ingredient_clean = ingredient_name.lower().strip()

        # Rechercher l'ingrédient dans les données PCA
        matching_rows = self.pca_data[
            self.pca_data["Descrip"]
            .str.lower()
            .str.contains(ingredient_clean, na=False)
        ]

        if matching_rows.empty:
            print(
                f"⚠️ Ingrédient '{ingredient_name}' non trouvé dans les données PCA"
            )
            return None

        # Prendre la première correspondance
        row = matching_rows.iloc[0]
        print(f"🔍 Ingrédient trouvé: {ingredient_name} → {row['Descrip']}")

        # Copier les données pour filtrage selon contraintes
        df_filtered = self.pca_data.copy()

        # 03/12 ajout filtrage sur category_llm
        # df_filtered = df_filtered[df_filtered['Category_LLM'] == row['Category_LLM']]

        # Appliquer les filtres de contraintes
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
                    # Garder seulement les ingrédients qui respectent la contrainte OU l'ingrédient original
                    if col in df_filtered.columns:
                        df_filtered = df_filtered[
                            (df_filtered[col] == allowed_val)
                            | (
                                df_filtered["Descrip"].str.lower()
                                == ingredient_clean
                            )
                        ]
                        print(f"🔧 Contrainte appliquée: {constraint_name}")

        # Colonnes PCA
        macro_cols = ["PCA_macro_1", "PCA_macro_2", "PCA_macro_3"]
        micro_cols = ["PCA_micro_1", "PCA_micro_2"]

        # Vérifier que les colonnes existent
        available_macro_cols = [
            col for col in macro_cols if col in df_filtered.columns
        ]
        available_micro_cols = [
            col for col in micro_cols if col in df_filtered.columns
        ]

        if not available_macro_cols and not available_micro_cols:
            print("❌ Aucune colonne PCA disponible pour le calcul de distance")
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

        # Exclure l'ingrédient original
        df_filtered = df_filtered[df_filtered["Descrip"] != row["Descrip"]]

        if df_filtered.empty:
            print("⚠️ Aucun substitut trouvé après application des contraintes")
            return None

        # Calculer les distances globales (combinaison macro + micro)
        df_filtered = df_filtered.copy()

        # Calculer distance macro
        if available_macro_cols:
            df_filtered["dist_macro"] = df_filtered[available_macro_cols].apply(
                lambda x: euclidean_distance(macro_vec, x.values), axis=1
            )
        else:
            df_filtered["dist_macro"] = 0

        # Calculer distance micro
        if available_micro_cols:
            df_filtered["dist_micro"] = df_filtered[available_micro_cols].apply(
                lambda x: euclidean_distance(micro_vec, x.values), axis=1
            )
        else:
            df_filtered["dist_micro"] = 0

        # Score global combiné
        df_filtered["global_score"] = (
            macro_weight * df_filtered["dist_macro"]
            + micro_weight * df_filtered["dist_micro"]
        )

        # Trier par score global et prendre les k meilleurs
        best_substitutes = df_filtered.nsmallest(k, "global_score")

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

    def juge_substitut(self, candidats):
        """
        Fonction qui fait le choix final de l'ingrédient qui sera substitué parmis la liste des candidats

        Args:
            candidats: Liste des ingrédients candidats (extraits de get_neighbors_pca() )

        Returns:
            ingredient_id
        """
        pass

    def substituer_ledit_ingr(
        self, ingredient: str, contraintes: TransformConstraints
    ) -> tuple[str, bool]:
        """
        Trouve un substitut pour l'ingrédient donné en utilisant PCA en priorité

        Args:
            ingredient: Ingrédient à substituer
            contraintes: Contraintes nutritionnelles

        Returns:
            Tuple (ingrédient_substitué, substitution_effectuée)
        """
        # Essayer d'abord avec PCA
        pca_result = self.get_neighbors_pca(ingredient, contraintes, k=3)

        if pca_result and pca_result["best_substitutes"]:
            # Prendre le meilleur substitut PCA
            best_substitute = pca_result["best_substitutes"][0]
            substitute_name = best_substitute["name"]

            print(
                f"🎯 {ingredient} → {substitute_name} (PCA score: {best_substitute['global_score']:.3f})"
            )
            return substitute_name, True

        return ingredient, False

    def adapter_recette_avec_llm(
        self, recipe: Recipe, substitutions: Dict
    ) -> str:
        """Adapte les étapes de la recette avec les substitutions via LLM"""

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
            print(f"⚠️ Erreur LLM: {e}")
            # Fallback : adaptation manuelle simple
            adapted_steps = recipe.steps
            adapted_steps = [
                step.replace(original, substitute)
                for original, substitute in substitutions.items()
                for step in adapted_steps
            ]
            return adapted_steps

    def transform(
        self,
        recipe: Recipe,
        ingredients_to_remove: List[str],
        constraints: TransformConstraints,
    ) -> TransformResponse:
        success = True

        try:
            # Step 1: Compute original recipe score and nutrition
            original_nutrition = self.calculer_nutrition_recette(
                ingredient_list=recipe.ingredients,
                ingredient_quantity=recipe.quantity_ingredients,
            )
            print("Step 1 completed")
            # TODO
            # Step 2: Constraint analysis
            # request.constraints
            # Parse constraint to sql conditions

            # TODO
            # Step 3: Choose ingredient to replace
            # Getting ingredient replacement list
            if ingredients_to_remove is not None:
                ingredients_to_substitute = ingredients_to_remove
            else:
                ingredients_to_substitute = self._extract_ingredients_from_text(
                    recipe.ingredients
                )
                # TODO : choose ingredient with an LLM ?

            print("Step 3 completed")
            # Step 4: Getting new ingredient and substitute them
            ingredients_to_substitute_matched = [
                self.ingredients_cache[ing]["name"]
                for ing in ingredients_to_substitute
            ]
            substitutions = {}
            substitution_count = 0
            new_quantity = recipe.quantity_ingredients
            for i, ingredient in enumerate(ingredients_to_substitute_matched):
                substitute, was_substituted = self.substituer_ledit_ingr(
                    ingredient, constraints
                )

                if was_substituted:
                    substitutions[ingredients_to_substitute[i]] = substitute
                    ingredient = substitute
                    substitution_count += 1
            new_ingredients = [
                substitutions.get(ingredient, ingredient)
                for ingredient in recipe.ingredients
            ]

            print("Step 4 completed")
            # Step 5: Compute new health score
            new_nutrition = self.calculer_nutrition_recette(
                new_ingredients, new_quantity
            )
            new_recipe = Recipe(
                name=recipe.name,
                ingredients=new_ingredients,
                quantity_ingredients=new_quantity,
                minutes=recipe.minutes,
                steps=recipe.steps,
            )
            print("Step 5 completed")
            # Repeat step 3-5
            # if original_nutrition.score>=new_nutrition.score:

            # Step 6: Adapt recipe step with LLM
            notes = []
            if substitutions:
                new_recipe.steps, notes = self.adapter_recette_avec_llm(
                    new_recipe, substitutions
                )
            print("Step 6 completed")

            # Step 7 : Build output
            response = TransformResponse(
                recipe=new_recipe,
                original_name=recipe.name,
                transformed_name=new_recipe.name,
                substitutions=None,
                nutrition_before=original_nutrition,
                nutrition_after=new_nutrition,
                success=success,
                message="\n".join(notes),
            )
            print("Step 7 completed")
            return response

        except Exception as e:
            print(f"Error in transformation process: {e}")
            print("\nTraceback complet:")
            traceback.print_exc()
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
    loaded_request: dict = json.loads(request)
    input_recipe: Recipe = Recipe(**loaded_request["recipe"])
    input_ingredients_to_remove: List[str] = loaded_request.get(
        "ingredients_to_remove"
    )
    input_constraints: TransformConstraints = TransformConstraints(
        **loaded_request.get("constraints", {})
    )

    service = TransformService(session)
    # Call transform service
    output = service.transform(
        input_recipe, input_ingredients_to_remove, input_constraints
    )

    return format_output(to_dict(output))
