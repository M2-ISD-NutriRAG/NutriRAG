from typing import Optional
from app.models.transform import TransformConstraints, TransformResponse
from app.services.snowflake_client import get_snowflake_session
from app.models.transform import TransformResponse, Substitution, NutritionDelta


class TransformService:
    # Service de transformation de recettes
    
    async def transform(
        self,
        recipe_id: int,
        goal: str,
        constraints: Optional[TransformConstraints] = None
    ) -> TransformResponse:
        # Transformer une recette en fonction de l'objectif et des contraintes
        # TODO: Équipe 3 - Implémentation de la logique de transformation
        # session = get_snowflake_session()
        
        # raise NotImplementedError("Équipe 3: Implémentation nécessaire - Logique de transformation")
        # MOCK DATA – À remplacer par la vraie logique de l’équipe 3

        return TransformResponse(
            recipe_id=recipe_id,
            original_name="Pâtes à la crème et au bacon",
            transformed_name="Pâtes protéinées au yaourt grec et dinde",
            
            substitutions=[
                Substitution(
                    original_ingredient="Crème fraîche",
                    substitute_ingredient="Yaourt grec 0%",
                    original_quantity=100.0,
                    substitute_quantity=120.0,
                    reason="Moins de matières grasses et meilleure teneur en protéines"
                ),
                Substitution(
                    original_ingredient="Bacon",
                    substitute_ingredient="Blanc de dinde",
                    original_quantity=120.0,
                    substitute_quantity=120.0,
                    reason="Moins gras et plus riche en protéines"
                ),
                Substitution(
                    original_ingredient="Pâtes blanches",
                    substitute_ingredient="Pâtes complètes",
                    original_quantity=200.0,
                    substitute_quantity=200.0,
                    reason="Index glycémique plus bas et plus de fibres"
                )
            ],

            nutrition_before={
                "calories": 720,
                "protein_g": 22,
                "carbs_g": 74,
                "fat_g": 38,
                "fiber_g": 4,
                "sodium_mg": 890,
                "score_health": 42
            },

            nutrition_after={
                "calories": 480,
                "protein_g": 42,
                "carbs_g": 55,
                "fat_g": 14,
                "fiber_g": 9,
                "sodium_mg": 420,
                "score_health": 78
            },

            delta=NutritionDelta(
                calories=-240,
                protein_g=+20,
                fat_g=-24,
                carbs_g=-19,
                fiber_g=+5,
                sodium_mg=-470,
                score_health=+36
            ),

            success=True,
            message=f"Transformation réussie selon l'objectif '{goal}'"
        )