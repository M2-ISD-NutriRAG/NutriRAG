import traceback
import pandas as pd
import numpy as np
import threading
from typing import Dict, List, Any, Optional, Tuple

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

class TransformService:
    _pca_data_cache = None
    _pca_lock = threading.Lock()
    # check if async necessary for the constructor
    def __init__(self, client: Optional[SnowflakeClient] = None):
        self.client = client if client else SnowflakeClient()
        self.ingredients_cache: Dict[str, Optional[Dict]] = {}
        self.pca_data = None  # ingredient coordinates for clustering 

    def _get_ingredient_nutrition(self, ingredient_name: str) -> Optional[Dict]:
        """
        Retrieve nutritional information of an ingredient from the database.
        
        Args:
            ingredient_name: ingredient name to search
            
        Returns:
            Dict with nutritional information or None if not found
        """
        ingredient_key = ingredient_name.lower().strip()
        if ingredient_key in self.ingredients_cache:
            return self.ingredients_cache[ingredient_key]

        try:
            ingredient_name = ingredient_name.replace("'", "''").lower()

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
                "INGREDIENT" as matched_ingredient
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
                    im."INGREDIENT"
                FROM NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS ci
                FULL OUTER JOIN NUTRIRAG_PROJECT.CLEANED.INGREDIENTS_MATCHING im
                    ON im."NDB_NO" = ci."NDB_NO"
                WHERE 
                    LOWER(ci."DESCRIP") LIKE %s
                    OR LOWER(im."INGREDIENT") LIKE %s
            ) AS result
            """

            result = self.client.execute(query, params=(ingredient_name, ingredient_name), fetch="all")
            
            if result:
                # Take the best match (exact match prioritized)
                best_match = None
                exact_match = None
                
                for row in result:
                    matched_ingredient = row[-1].lower() if row[-1] is not None else row[0].lower()
                    descrip = row[0].lower() if row[0] is not None else row[-1].lower()
                    
                    # Use safe_float for all conversions
                    nutrition_data = {
                        'name': descrip,
                        'matched_ingredient': matched_ingredient,
                        'protein': float(row[1]),
                        'saturated_fats': float(row[2]),
                        'fat': float(row[3]),
                        'carbs': float(row[4]),
                        'sodium': float(row[5]),
                        'fiber': float(row[6]),
                        'sugar': float(row[7]),
                        'calories': float(row[8])
                    }
                    
                    # Exact match with the matched ingredient
                    if matched_ingredient == ingredient_key:
                        exact_match = nutrition_data
                        break
                    # Best partial match
                    elif ingredient_key in matched_ingredient or any(word in matched_ingredient for word in ingredient_key.split()):
                        if best_match is None:
                            best_match = nutrition_data
                
                result_data = exact_match or best_match
                
                if result_data:
                    # Cache the result
                    self.ingredients_cache[ingredient_key] = result_data
                    print(f" Ingredient found: {ingredient_name} → {result_data['name']}")
                    return result_data
            
            # Not found - cache negative result
            self.ingredients_cache[ingredient_key] = None
            print(f"⚠️ Ingredient not found in the database: {ingredient_name}")
            return None
            
        except Exception as e:
            print(f"❌_get_ingredient : Error searching ingredient '{ingredient_name}': {e}")
            return None

    def calculate_health_score(self, total_nutrition: NutritionDelta) -> float:
        """
        Calculates Recipe index health score
        """
        score = (100 
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

    def calculate_recipe_nutrition(self, ingredient_list: List[str], ingredient_quantity: List[str]) -> NutritionDelta:
        """Calcule la nutrition totale de la recette"""

        total_nutrition = NutritionDelta()
        for ingredient, qty in zip(ingredient_list, ingredient_quantity):
            qty = int(qty) # To change if multi type
            ingredient_data = self._get_ingredient_nutrition(ingredient)
            
            if ingredient_data:
                # Ensure all values are floats before calculations
                calories = ceil(ingredient_data['calories']/NUTRIENT_BASIS_GRAMS)
                protein = ceil(ingredient_data['protein']/NUTRIENT_BASIS_GRAMS)
                saturated_fat = ceil(ingredient_data['saturated_fats']/NUTRIENT_BASIS_GRAMS)
                fat = ceil(ingredient_data['fat']/NUTRIENT_BASIS_GRAMS)
                carbs = ceil(ingredient_data['carbs']/NUTRIENT_BASIS_GRAMS)
                fiber = ceil(ingredient_data['fiber']/NUTRIENT_BASIS_GRAMS)
                sodium = ceil(ingredient_data['sodium']/NUTRIENT_BASIS_GRAMS)
                sugar = ceil(ingredient_data['sugar']/NUTRIENT_BASIS_GRAMS)
                
                total_nutrition.calories += calories * qty
                total_nutrition.protein_g += protein * qty
                total_nutrition.fat_g += fat * qty
                total_nutrition.saturated_fats_g += saturated_fat * qty
                total_nutrition.sugar_g += sugar * qty
                total_nutrition.sodium_mg += sodium * qty
                total_nutrition.carb_g += carbs * qty
                total_nutrition.fiber_g += fiber * qty
        
        total_nutrition.score_health = self.calculate_health_score(total_nutrition)
        return total_nutrition

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
            recipe: Recipe,
            ingredients_to_remove: List[str],
            constraints: TransformConstraints)-> TransformResponse:
        """
        Transform a recipe based on constraints and ingredients to remove, full pipeline
        """
        success = True
        self.ensure_pca_loaded()
        
        try:
            # Step 1: Compute original recipe score and nutrition
            original_nutrition = self.calculate_recipe_nutrition(ingredient_list=recipe.ingredients, ingredient_quantity=recipe.quantity_ingredients)
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
                ingredients_to_substitute = self._extract_ingredients_from_text(recipe.ingredients)
                # TODO : choose ingredient with an LLM ?

            print("Step 3 completed")
            # Step 4: Getting new ingredient and substitute them
            print(self.ingredients_cache)
            ingredients_to_substitute_matched = [self.ingredients_cache[ing]["name"] for ing in ingredients_to_substitute]
            print("dict problem")
            substitutions = {}
            substitution_count = 0
            new_quantity = recipe.quantity_ingredients
            for i, ingredient in enumerate(ingredients_to_substitute_matched):
                substitute, was_substituted = self.substituer_ledit_ingr(ingredient, constraints)
                
                if was_substituted:
                    substitutions[ingredients_to_substitute[i]] = substitute
                    ingredient = substitute
                    substitution_count += 1
            new_ingredients = [substitutions.get(ingredient, ingredient) for ingredient in recipe.ingredients]

            print("Step 4 completed")
            # Step 5: Compute new health score
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
            if substitutions:
                new_recipe.steps, notes = self.adapt_recipe_with_llm(new_recipe, substitutions)
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

