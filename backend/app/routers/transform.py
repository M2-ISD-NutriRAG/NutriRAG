import pickle
from fastapi import APIRouter, HTTPException
from app.models.transform import TransformRequest, TransformResponse
from app.services.transform_service import TransformService
from shared.snowflake.client import SnowflakeClient


router = APIRouter()
transform_service = TransformService(SnowflakeClient())


@router.post("/", response_model=TransformResponse)
async def transform_recipe(request: TransformRequest):
    # Transformer une recette pour être plus saine ou répondre à des contraintes spécifiques
    """
    Example:
    ```json
    {
      "recipe_id": 12345,
      "goal": "healthier",
      "constraints": {
        "no_lactose": true,
        "increase_protein": true,
        "decrease_calories": true,
        ...
      }
    }
    ```
    """
    try:
        # TODO: Équipe 3 - Implémentation de la logique de transformation
        with open("request.pkl", "rb") as file:
            request = pickle.load(file)

        
        result = await transform_service.transform(
            recipe=request.recipe,
            ingredients_to_remove=request.ingredients_to_remove,
            constraints=request.constraints
        )

        return result
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Équipe 3: Transform implementation needed - Substitutions + nutrition recalc",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/substitutions/{ingredient}")
async def get_substitutions(ingredient: str, goal: str = "healthier"):
    # Obtenir des suggestions de substitutions pour un ingrédient donné
    # TODO: Équipe 3 - Requête de la base de données de substitutions

    raise HTTPException(
        status_code=501,
        detail="Équipe 3: Implémentation nécessaire - Suggestions de substitutions",
    )


@router.post("/validate")
async def validate_transformation(
    original_nutrition: dict, transformed_nutrition: dict
):
    # Valider que la transformation respecte les critères de santé
    # TODO: Équipe 3 - Implémentation de la logique de validation

    raise HTTPException(
        status_code=501,
        detail="Équipe 3: Implémentation nécessaire - Validation de la transformation",
    )