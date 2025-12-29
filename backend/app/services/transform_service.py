import traceback
from typing import Dict, List, Optional

from shared.snowflake.client import SnowflakeClient

from app.models.transform import (
    TransformConstraints,
    TransformResponse,
    NutritionDelta,
    Recipe
)
from math import ceil


NUTRIENT_BASIS_GRAMS = 100

class TransformService:
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
    # Recipe transformaiton service


    
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
            # else:
                # ingredients_to_substitute = self._extract_ingredients_from_text(recipe.ingredients)
                # TODO : choose ingredient with an LLM ?

            print("Step 3 completed")
            # Step 4: Getting new ingredient and substitute them
            ingredients_to_substitute_matched = []
            orig_ings = []  # keep the original ingredient corresponding

            for ing in ingredients_to_substitute:
                cached = self.ingredients_cache.get(ing)
                if isinstance(cached, dict):
                    name = cached.get("name")
                    if name:  # keep if ok
                        ingredients_to_substitute_matched.append(name)
                        orig_ings.append(ing)

            substitutions = {}
            substitution_count = 0
            new_quantity = recipe.quantity_ingredients
            for original, matched in zip(orig_ings, ingredients_to_substitute_matched):
                substitute, was_substituted = "uncomment later", False  # self.substituer_ledit_ingr(matched, constraints)

                if was_substituted:
                    substitutions[original] = substitute
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

