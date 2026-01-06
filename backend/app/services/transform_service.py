import traceback
import pandas as pd
import numpy as np
import threading
from typing import Dict, List, Any, Optional, Tuple

from backend.app.models.recipe import NutritionDetailed
from backend.app.services.recipe_index_score import compute_nutrition_for_ingredient
from shared.snowflake.client import SnowflakeClient

from app.models.transform import (
    TransformConstraints, 
    TransformationType, 
    TransformRequest,
    TransformResponse,
    NutritionDelta,
    Recipe
)
from math import ceil

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
    def __init__(self, client: Optional[SnowflakeClient] = None):
        self.client = client if client else SnowflakeClient()
        self.ingredients_cache: Dict[str, Optional[Dict]] = {}
        self.recipe_qty_cache: Dict[str, List[Tuple[str, Optional[float]]]] = {}
        self.recipe_nutrition_cache: Dict[str, Dict[str, Optional[Dict[str, Any]]]] = {}
        self.pca_data = None  # ingredient coordinates for clustering 
        self._load_pca_data()

    def fetch_recipe_quantities(self, recipe_id: str) -> Dict[str, Optional[float]]:
            """
            Returns list of (ingredient_string, qty_g_or_none) from INGREDIENTS_QUANTITY.
            Cached per recipe.
            """
            if recipe_id in self.recipe_qty_cache:
                return self.recipe_qty_cache[recipe_id]

            query = """
            SELECT
                INGREDIENTS,
                QTY_G
            FROM NUTRIRAG_PROJECT.RAW.INGREDIENTS_QUANTITY
            WHERE ID = %s
            """

            rows = self.client.execute(query, params=(recipe_id,), fetch="all") or []
            out: Dict[str, Optional[float]] = {}
            for ing, qty in rows:
                if ing is None:
                    continue  # ingredient name missing is unusable as a dict key
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

        # Build keys we will query (lower/trim like in SQL)
        keys = [ (s or "").strip().lower() for s in ingredients ]
        keys = [k for k in keys if k]  # remove empty
        unique_keys = sorted(set(keys))

        # Only query missing keys
        missing = [k for k in unique_keys if k not in self.recipe_nutrition_cache[recipe_id]]
        if not missing:
            return self.recipe_nutrition_cache[recipe_id]

        placeholders = ", ".join(["%s"] * len(missing))

        query = f"""
        WITH ranked AS (
            SELECT
                LOWER(TRIM(im.INGREDIENT_FROM_RECIPE_NAME)) AS ING_KEY,
                ci."ENERGY_KCAL",
                ci."PROTEIN_G",
                ci."FAT_G",
                ci."SATURATED_FATS_G",
                ci."CARB_G",
                ci."FIBER_G",
                ci."SUGAR_G",
                ci."SODIUM_MG",
                ci."CALCIUM_MG",
                ci."IRON_MG",
                ci."MAGNESIUM_MG",
                ci."POTASSIUM_MG",
                ci."VITC_MG",
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(TRIM(im.INGREDIENT_FROM_RECIPE_NAME))
                    ORDER BY ci."SCORE_SANTE" DESC NULLS LAST
                ) AS RN
            FROM NUTRIRAG_PROJECT.RAW.INGREDIENTS_MATCHING im
            LEFT JOIN NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS ci
                ON im.INGREDIENT_ID = ci."NDB_NO"
            WHERE im.RECIPE_ID = %s
              AND LOWER(TRIM(im.INGREDIENT_FROM_RECIPE_NAME)) IN ({placeholders})
        )
        SELECT
            ING_KEY,
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
            "VITC_MG"
        FROM ranked
        WHERE RN = 1;
        """

        params = (recipe_id, *missing)

        rows = self.client.execute(query, params=params, fetch="all") or []

        # Default missing keys to None (so we don't re-query forever)
        for k in missing:
            self.recipe_nutrition_cache[recipe_id][k] = None

        for row in rows:
            ing_key = row[0]               # already lower/trim
            vals = row[1:]                 # nutrients
            nutr = dict(zip(NUTRITION_COLS, vals))
            self.recipe_nutrition_cache[recipe_id][ing_key] = nutr

        return self.recipe_nutrition_cache[recipe_id]
    

    def compute_recipe_nutrition_totals(
        self,
        recipe_id: str,
        ingredients: List[str],
        serving_size: float,
        servings: float,
    ) -> NutritionDetailed:
        """
        Compute recipe nutrition information for all ingredients

        Parameters
        ----------
        ingredients_amounts : recipe ingredients quantity dict
        nutrition_table : recipe ingredients nutrition dict
        Returns
        -------
        NutritionDetailed
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
            fill_qty = max(total_weight - known_weight, 0.0) / unknown_count * 0.5
        else:
            fill_qty = 0.0
        
        recipe_nutrition = NutritionDetailed(
            calories=0.0,
            protein_g=0.0,
            fat_g=0.0,
            saturated_fat_g=0.0,
            carbs_g=0.0,
            fiber_g=0.0,
            sugar_g=0.0,
            sodium_mg=0.0,
            calcium_mg=0.0,
            iron_mg=0.0,
            magnesium_mg=0.0,
            potassium_mg=0.0,
            vitamin_c_mg=0.0,
        )
        for name, nutrition in ingredients_nutrition.items():
            if nutrition is None:
                continue
            quantity = ingredients_quantity.get(name) if not None else fill_qty
            factor = float(quantity) / NUTRIENT_BASIS_GRAMS

            recipe_nutrition.calories += nutrition.calories * factor
            recipe_nutrition.protein_g += nutrition.protein_g * factor
            recipe_nutrition.fat_g += nutrition.fat_g 
            recipe_nutrition.saturated_fat_g += nutrition.saturated_fat_g * factor
            recipe_nutrition.carbs_g += nutrition.carbs_g * factor
            recipe_nutrition.fiber_g += nutrition.fiber_g * factor
            recipe_nutrition.sugar_g += nutrition.sugar_g * factor
            recipe_nutrition.sodium_mg += nutrition.sodium_mg * factor

            recipe_nutrition.calcium_mg += nutrition.calcium_mg * factor
            recipe_nutrition.iron_mg += nutrition.iron_mg * factor
            recipe_nutrition.magnesium_mg += nutrition.magnesium_mg * factor
            recipe_nutrition.potassium_mg += nutrition.potassium_mg * factor
            recipe_nutrition.vitamin_c_mg += nutrition.vitamin_c_mg * factor

        return recipe_nutrition

    def compute_rhi_score(ingredients_amounts: Dict[str, float],
    nutrition_table: Dict[str, Dict[str, Any]]):
        """
        Compute recipe RHI score based on ingredients nutrition

        Parameters
        ----------
        ingredients_amounts : recipe ingredients quantity dict
        nutrition_table : recipe ingredients nutrition dict
        Returns
        -------
        float
            RHI score for the  recipe
        """
    

    def ensure_pca_loaded(self):
        if TransformService._pca_data_cache is None:
            with TransformService._pca_lock:
                if TransformService._pca_data_cache is None:
                    TransformService._pca_data_cache = self.load_pca_data_from_snowflake()
        self.pca_data = TransformService._pca_data_cache
    
    def load_pca_data(self):
        """Load PCA data from Snowflake or CSV as fallback"""
        try:
            print(" Chargement des données PCA depuis CSV (ingredients_with_clusters.csv)...")
            
            # Charger le fichier CSV
            csv_path = "ingredients_with_clusters.csv"
            df_csv = pd.read_csv(csv_path)
            
            # Adapter les noms de colonnes pour correspondre au format attendu
            self.pca_data = df_csv.rename(columns={
                'Energy_kcal': 'ENERGY_KCAL',
                'Protein_g': 'PROTEIN_G',
                'Saturated_fats_g': 'SATURATED_FATS_G', 
                'Fat_g': 'FAT_G',
                'Carb_g': 'CARB_G',
                'Sodium_mg': 'SODIUM_MG',
                'Sugar_g': 'SUGAR_G'
            })
            
            # Ajouter des colonnes de contraintes par défaut (pas disponibles dans le CSV)
            self.pca_data['is_lactose'] = 0
            self.pca_data['is_gluten'] = 0 
            self.pca_data['contains_nuts'] = 0
            self.pca_data['is_vegetarian'] = 0
            self.pca_data['is_vegetable'] = 0
            
            # Logique simple pour définir quelques contraintes basées sur le nom
            for idx, row in self.pca_data.iterrows():
                descrip_lower = str(row['Descrip']).lower()
                
                # Détection lactose (produits laitiers)
                if any(word in descrip_lower for word in ['milk', 'cheese', 'butter', 'cream', 'yogurt']):
                    self.pca_data.at[idx, 'is_lactose'] = 1
                
                # Détection gluten (céréales, pain, etc.)
                if any(word in descrip_lower for word in ['wheat', 'bread', 'flour', 'pasta', 'cereal']):
                    self.pca_data.at[idx, 'is_gluten'] = 1
                
                # Détection noix
                if any(word in descrip_lower for word in ['nut', 'almond', 'peanut', 'walnut', 'pecan']):
                    self.pca_data.at[idx, 'contains_nuts'] = 1
                
                # Détection végétarien (pas de viande/poisson)
                if not any(word in descrip_lower for word in ['beef', 'pork', 'chicken', 'fish', 'meat', 'turkey', 'lamb']):
                    self.pca_data.at[idx, 'is_vegetarian'] = 1
                
                # Détection végétal (fruits, légumes, etc.)
                if any(word in descrip_lower for word in ['vegetable', 'fruit', 'bean', 'pea', 'lentil', 'spinach', 'carrot', 'tomato']):
                    self.pca_data.at[idx, 'is_vegetable'] = 1
            
            print(f"[1.4-_load_pca_data] ✅ Données CSV chargées: {len(self.pca_data)} ingrédients")
            
        except Exception as e:
            print(f"[1.5-_load_pca_data] ❌ Erreur chargement CSV: {e}")
            self.pca_data = None
    
    def get_neighbors_pca(self, ingredient_name: str, constraints: TransformConstraints = None, 
                         micro_weight: float = 0.3, macro_weight: float = 0.7, k: int = 5) -> Dict:
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
            print("❌ PCA Data not available")
            return None
            
        # Clean ingredient name
        ingredient_clean = ingredient_name.lower().strip()
        
        # Search for ingredient in PCA Data 
        matching_rows = self.pca_data[self.pca_data['Descrip'].str.lower().str.contains(ingredient_clean, na=False)]
        
        if matching_rows.empty:
            print(f"⚠️ Ingredient '{ingredient_name}' not found in PCA data")
            return None
            
        # Take the first match
        row = matching_rows.iloc[0]
        print(f"🔍 Ingredient found: {ingredient_name} → {row['Descrip']}")
        
        # Copy data for filtering based on constraints
        df_filtered = self.pca_data.copy()

        # Filter addition for category_llm
        if 'Category_LLM' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Category_LLM'] == row['Category_LLM']]
        else:
            print("⚠️ Column 'Category_LLM' absent from PCA data, category filtering ignored")
        
        # Apply constraint filters
        if constraints:
            CONSTRAINT_TO_COLUMN = {
                "no_lactose": ("is_lactose", 0),
                "no_gluten": ("is_gluten", 0),
                "no_nuts": ("contains_nuts", 0),
                "vegetarian": ("is_vegetarian", 1),
                "vegan": ("is_vegetable", 1)
            }
            
            for constraint_name, (col, allowed_val) in CONSTRAINT_TO_COLUMN.items():
                if getattr(constraints, constraint_name, False):
                    # Keep only ingredients that meet the constraint OR the original ingredient
                    if col in df_filtered.columns:
                        df_filtered = df_filtered[
                            (df_filtered[col] == allowed_val) |
                            (df_filtered['Descrip'].str.lower() == ingredient_clean)
                        ]
                        print(f"🔧 Constraint applied: {constraint_name}")
        
        # PCA columns
        macro_cols = ['PCA_macro_1', 'PCA_macro_2', 'PCA_macro_3']
        micro_cols = ['PCA_micro_1', 'PCA_micro_2']
        
        # Check that columns exist
        available_macro_cols = [col for col in macro_cols if col in df_filtered.columns]
        available_micro_cols = [col for col in micro_cols if col in df_filtered.columns]
        
        if not available_macro_cols and not available_micro_cols:
            print("❌ No PCA columns available for distance calculation")
            return None
        
        macro_vec = row[available_macro_cols].values if available_macro_cols else np.array([])
        micro_vec = row[available_micro_cols].values if available_micro_cols else np.array([])
        
        def euclidean_distance(a, b):
            return np.linalg.norm(a - b) if len(a) > 0 and len(b) > 0 else 0
        
        # Exclude the original ingredient
        df_filtered = df_filtered[df_filtered['Descrip'] != row['Descrip']]
        
        if df_filtered.empty:
            print("⚠️ No substitute found after applying constraints")
            return None
        
        # Calculate global distances (macro + micro combination)
        df_filtered = df_filtered.copy()
        
        # Calculate macro distance
        if available_macro_cols:
            df_filtered['dist_macro'] = df_filtered[available_macro_cols].apply(
                lambda x: euclidean_distance(macro_vec, x.values), axis=1)
        else:
            df_filtered['dist_macro'] = 0
        
        # Calculate micro distance  
        if available_micro_cols:
            df_filtered['dist_micro'] = df_filtered[available_micro_cols].apply(
                lambda x: euclidean_distance(micro_vec, x.values), axis=1)
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
            result["best_substitutes"].append({
                "name": substitute_row['Descrip'],
                "global_score": substitute_row['global_score'],
                "macro_distance": substitute_row['dist_macro'],
                "micro_distance": substitute_row['dist_micro'],
                "nutrition": {
                    "calories": substitute_row['ENERGY_KCAL'],
                    "protein": substitute_row['PROTEIN_G'],
                    "saturated_fat": substitute_row['SATURATED_FATS_G'],
                    "sodium": substitute_row['SODIUM_MG'],
                    "sugar": substitute_row['SUGAR_G']
                }
            })
        
        return result
    
    def get_score_sante(self, ingredient_name: str) -> float:
        """
        TODO
        """
        return 1
    



    def judge_substitute(self, candidats):
        """
        TODO
        Final ingredient choice between list of candidats

        Args:
            candidats: list of possible ingredients to substitute with (extracted from get_neighbors_pca() )

        Returns:
            ingredient_id
        """
        best_ingr = None

        if not candidats:
            print("Pas de candidats pour le susbstitut")
            return None
        for candidat in candidats:
            if best_ingr is None:
                best_ingr = candidat
            else:
                if self.get_score_sante(candidat) > self.get_score_sante(best_ingr): # CHANGER AVEC LE VRAI NOM DE FCT
                    best_ingr = candidat
                    
        return best_ingr

    
    def substitute_ingr(self, ingredient: str, contraintes: TransformConstraints) -> Tuple[str, bool]:
        """
        Finds a substitute for the given ingredient using PCA in priority
        
        Args:
            ingredient: ingredient to substitute
            contraintes: nutritional constraints
        
        Returns:
            Tuple (substituted_ingredient, substitution_performed)
        """
        # Try with PCA first
        pca_result = self.get_neighbors_pca(ingredient, contraintes, k=3)
        
        if pca_result and pca_result["best_substitutes"]:
            # Take the best PCA substitute
            best_substitute = pca_result["best_substitutes"][0]
            substitute_name = best_substitute["name"]
            
            print(f"🎯 {ingredient} → {substitute_name} (PCA score: {best_substitute['global_score']:.3f})")
            return substitute_name, True
        
        return ingredient, False
    
    def adapt_recipe_with_llm(self, recipe: Recipe, substitutions: Dict) -> str:
        """
        Adapt the recipe steps with substitutions via LLM
        """
        
        # Building the prompt for the LLM
        base_prompt = f'''You are an expert chef specializing in recipe adaptation and ingredient substitution.

        ORIGINAL RECIPE:
        Name: {recipe.name}
        Ingredients: {recipe.ingredients}
        Steps: {recipe.steps}

        SUBSTITUTIONS TO APPLY:
        '''

        for original, substitute in substitutions.items():
            base_prompt += f"- Replace '{original}' with '{substitute}'\n"

        base_prompt += '''
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

        ADAPTED RECIPE STEPS:'''

        try:
            # Échapper les guillemets simples pour éviter les erreurs SQL
            prompt_escaped = base_prompt.replace("'", "''")

            # Construire la requête SQL avec le prompt échappé
            llm_query = """
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                    %s
                ) AS adapted_steps
            """

            llm_response = self.client.execute(llm_query, params=(prompt_escaped,), fetch="all")
            parsed_steps = llm_response[0][0].strip().split("\n")
            new_steps = []
            notes = []
            for step in parsed_steps:
                if len(step)>0:
                    if step[0].isdigit():
                        new_steps.append(step)
                    elif str.startswith(step.lower(), "note"):
                        notes.append(step[6:].strip())
            return new_steps, notes
            
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            # Fallback: simple manual adaptation
            adapted_steps = recipe.steps
            adapted_steps = [step.replace(original, substitute) for original, substitute in substitutions.items() for step in adapted_steps]
            return adapted_steps, []
    
    async def transform(
            self,
            request: TransformRequest,
            recipe: Recipe,
            ingredients_to_remove: List[str],
            constraints: TransformConstraints)-> TransformResponse:
        """
        Transform a recipe based on constraints and ingredients to remove, full pipeline
        """
        success = True
        self.ensure_pca_loaded()
        
        try:
            transformation_type = request.constraints.transformation            # Step 1: Find ingredient to 'transform' depending on constrainsts if not received
            if request.ingredients_to_remove is not None:
                ingredients_to_substitute = request.ingredients_to_remove
            else:
                ingredients_to_substitute = self._extract_ingredients_from_text(recipe.ingredients)
                # TODO : code à rajouter 

            print("Step 1 completed")

            transformations = {}
            transformation_count = 0
            new_ingredients = recipe.ingredients # default value
            ## Step 2 based on transformation type
            if transformation_type == TransformationType.SUBSTITUTION:
                ## Step 2.1 Get new ingredients to substitute
                ingredients_to_substitute_matched = [
                    self.ingredients_cache[ing]["name"] 
                    for ing in ingredients_to_substitute]
                
                for original_ing, matched_name in zip(ingredients_to_substitute, ingredients_to_substitute_matched):
                    substitute, was_substituted = self.substitute_ingr(matched_name, constraints)
                    if was_substituted:
                        transformations[original_ing] = substitute
                        transformation_count += 1
                new_ingredients = [transformations.get(ingredient, ingredient) for ingredient in recipe.ingredients]
            elif transformation_type == TransformationType.ADD:
                # TODO
                pass
            elif transformation_type == TransformationType.DELETE:
                # TODO
                pass
            print("Step 2 completed")

            # Step 3 compute health score for new recipe
            new_nutrition = self.calculate_recipe_nutrition(new_ingredients, new_quantity)
            new_recipe = Recipe(
                name=recipe.name,
                ingredients=new_ingredients,
                quantity_ingredients=new_quantity,
                minutes=recipe.minutes,
                steps=recipe.steps
            )
            print("Step 5 completed")
            # Repeat step 3-5
            # if original_nutrition.score>=new_nutrition.score:


            # Step 6: Adapt recipe step with LLM
            if transformations:
                new_recipe.steps, notes = self.adapt_recipe_with_llm(new_recipe, transformations)
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
                message="\n".join(notes)
            )
            print("Step 7 completed")
            return response

        except Exception as e:
            print(f"Error in transformation process: {e}")
            print("\nTraceback complet:")
            traceback.print_exc()
            success= False
            response = TransformResponse(
                recipe=recipe,
                original_name=recipe.name,
                transformed_name=recipe.name,
                substitutions=None,
                nutrition_before=None,
                nutrition_after=None,
                success=success,
                message=None
            )

            return response

        
        # return TransformResponse(
        #     recipe_id=recipe_id,
        #     original_name="Pâtes à la crème et au bacon",
        #     transformed_name="Pâtes protéinées au yaourt grec et dinde",
            
        #     substitutions=[
        #         Substitution(
        #             original_ingredient="Crème fraîche",
        #             substitute_ingredient="Yaourt grec 0%",
        #             original_quantity=100.0,
        #             substitute_quantity=120.0,
        #             reason="Moins de matières grasses et meilleure teneur en protéines"
        #         ),
        #         Substitution(
        #             original_ingredient="Bacon",
        #             substitute_ingredient="Blanc de dinde",
        #             original_quantity=120.0,
        #             substitute_quantity=120.0,
        #             reason="Moins gras et plus riche en protéines"
        #         ),
        #         Substitution(
        #             original_ingredient="Pâtes blanches",
        #             substitute_ingredient="Pâtes complètes",
        #             original_quantity=200.0,
        #             substitute_quantity=200.0,
        #             reason="Index glycémique plus bas et plus de fibres"
        #         )
        #     ],

        #     nutrition_before={
        #         "calories": 720,
        #         "protein_g": 22,
        #         "carbs_g": 74,
        #         "fat_g": 38,
        #         "fiber_g": 4,
        #         "sodium_mg": 890,
        #         "score_health": 42
        #     },

        #     nutrition_after={
        #         "calories": 480,
        #         "protein_g": 42,
        #         "carbs_g": 55,
        #         "fat_g": 14,
        #         "fiber_g": 9,
        #         "sodium_mg": 420,
        #         "score_health": 78
        #     },

        #     delta=NutritionDelta(
        #         calories=-240,
        #         protein_g=+20,
        #         fat_g=-24,
        #         carbs_g=-19,
        #         fiber_g=+5,
        #         sodium_mg=-470,
        #         score_health=+36
        #     ),

        #     success=True,
        #     message=f"Transformation réussie selon l'objectif '{goal}'"
        # )

