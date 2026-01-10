import json
import traceback
from typing import List, Any, Dict
from snowflake.snowpark import Session


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


def transform_service(
    session: Session,
    recipe: dict,
    ingredients_to_remove: List[str],
    constraints: dict,
) -> str:
    """
    Template procedure

    Args:
    session: Snowpark session implicitly init by snowflake
    arg1: dict type argument
    arg2: list type argument

    Returns:
    output: JSON string containing output.
    """
    success = True

    try:
        # # Step 1: Compute original recipe score and nutrition
        # original_nutrition = self.calculer_nutrition_recette(ingredient_list=recipe.ingredients, ingredient_quantity=recipe.quantity_ingredients)
        # print("Step 1 completed")
        # # TODO
        # # Step 2: Constraint analysis
        # # request.constraints
        # # Parse constraint to sql conditions

        # # TODO
        # # Step 3: Choose ingredient to replace
        # # Getting ingredient replacement list
        # if ingredients_to_remove is not None:
        #     ingredients_to_substitute = ingredients_to_remove
        # else:
        #     ingredients_to_substitute = self._extract_ingredients_from_text(recipe.ingredients)
        #     # TODO : choose ingredient with an LLM ?

        # print("Step 3 completed")
        # # Step 4: Getting new ingredient and substitute them
        # print(self.ingredients_cache)
        # ingredients_to_substitute_matched = [self.ingredients_cache[ing]["name"] for ing in ingredients_to_substitute]
        # print("dict problem")
        # substitutions = {}
        # substitution_count = 0
        # new_quantity = recipe.quantity_ingredients
        # for i, ingredient in enumerate(ingredients_to_substitute_matched):
        #     substitute, was_substituted = self.substituer_ledit_ingr(ingredient, constraints)

        #     if was_substituted:
        #         substitutions[ingredients_to_substitute[i]] = substitute
        #         ingredient = substitute
        #         substitution_count += 1
        # new_ingredients = [substitutions.get(ingredient, ingredient) for ingredient in recipe.ingredients]

        # print("Step 4 completed")
        # # Step 5: Compute new health score
        # new_nutrition = self.calculer_nutrition_recette(new_ingredients, new_quantity)
        # new_recipe = Recipe(
        #     name=recipe.name,
        #     ingredients=new_ingredients,
        #     quantity_ingredients=new_quantity,
        #     minutes=recipe.minutes,
        #     steps=recipe.steps
        # )
        # print("Step 5 completed")
        # # Repeat step 3-5
        # # if original_nutrition.score>=new_nutrition.score:

        # # Step 6: Adapt recipe step with LLM
        # if substitutions:
        #     new_recipe.steps, notes = self.adapter_recette_avec_llm(new_recipe, substitutions)
        # print("Step 6 completed")
        new_recipe = recipe
        notes = ["test", "notes"]
        original_nutrition = {}
        new_nutrition = {}
        # Step 7 : Build output
        response = {
            "recipe": new_recipe,
            "original_name": recipe["name"],
            "transformed_name": new_recipe["name"],
            "substitutions": None,
            "nutrition_before": original_nutrition,
            "nutrition_after": new_nutrition,
            "success": success,
            "message": "\n".join(notes),
        }
        print("Step 7 completed")

    except Exception as e:
        print(f"Error in transformation process: {e}")
        print("\nTraceback complet:")
        traceback.print_exc()
        success = False
        response = {
            "recipe": recipe,
            "original_name": recipe["name"],
            "transformed_name": recipe["name"],
            "substitutions": None,
            "nutrition_before": None,
            "nutrition_after": None,
            "success": success,
            "message": None,
        }

    return response


def transform_recipe(session: Session, request: str) -> str:
    """
    Transform endpoint handler

    Args:
        session: Snowflake session to execute queries
        request: TransformRequest dict like
    Returns:
        output: TransformerResponse dict like

    Example :
    - input =
    ingredients = [
        "crabmeat",
        "cream cheese",
        "green onions",
        "garlic salt",
        "refrigerated crescent dinner rolls",
        "egg yolk",
        "water",
        "sesame seeds",
        "sweet and sour sauce",
    ]
    steps = [
        "heat over to 375 degrees",
        "spray large cookie sheet with non-stick cooking spray",
        "in small bowl , combine crabmeat , cream cheese , onions and garlic salt and mix well",
        "unroll both cans of dough",
        "separate into 16 triangles",
        "cut each triangle in half lengthwise to make 32 triangles",
        "place 1 teaspoon crab mixture on center of each triangle about 1 inch from short side of triangle",
        "fold short ends of each triangle over filling",
        "pinch sides to seal",
        "roll up",
        "place on sprayed cookie sheet",
        "in small bowl , combine egg yolk and water and mix well",
        "brush egg mixture over snacks",
        "sprinkle with sesame seed",
        "bake at 375 degrees for 15 to 20 minutes or until golden brown",
        "serve warn snacks with sweet-and-sour sauce",
    ]

    recipe = {
        "name": "crab filled crescent snacks",
        "ingredients": ingredients,
        "quantity_ingredients": ["1"] * len(ingredients),
        "minutes": 70.0,
        "steps": steps,
    }

    ingredients_to_remove = ["cream cheese"]

    constraints = {
        "transformation": "SUBSTITUTION",
        "no_lactose": False,
        "no_gluten": False,
        "no_nuts": False,
        "vegetarian": False,
        "vegan": False,
        "increase_protein": False,
        "decrease_sugar": False,
        "decrease_protein": False,
        "decrease_carbs": False,
        "decrease_calories": False,
        "decrease_sodium": False,
    }

    request = {
        "recipe": recipe,
        "ingredients_to_remove": ingredients_to_remove,
        "constraints": constraints,
    }

    - output = {
        "recipe": input_recipe,
        "original_name": input_recipe["name"],
        "transformed_name": "new_recipe",
        "substitutions": [
            {
                "original_ingredient": "string",
                "substitute_ingredient": "string",
                "original_quantity": 1.0,
                "substitute_quantity": 0.0,
                "reason": "string"
            }
        ],
        "nutrition_before": {
            "calories": 0.0,
            "protein_g": 0.0,
            "saturated_fats_g": 0.0,
            "fat_g": 0.0,
            "carb_g": 0.0,
            "fiber_g": 0.0,
            "sodium_mg": 0.0,
            "sugar_g": 0.0,
            "score_health": 0.0
        },
        "nutrition_after": {
            "calories": 0.0,
            "protein_g": 0.0,
            "saturated_fats_g": 0.0,
            "fat_g": 0.0,
            "carb_g": 0.0,
            "fiber_g": 0.0,
            "sodium_mg": 0.0,
            "sugar_g": 0.0,
            "score_health": 0.0
        },
        "success": True,
        "message": "string"
    }

    Create and call this procedure cf snow_proc_template.ipynb

    """

    # Input loading
    loaded_request: dict = json.loads(request)
    input_recipe: str = loaded_request["recipe"]
    input_ingredients_to_remove: str = loaded_request["ingredients_to_remove"]
    input_constraints: str = loaded_request["constraints"]

    output = transform_service(
        session, input_recipe, input_ingredients_to_remove, input_constraints
    )

    return format_output(output)
