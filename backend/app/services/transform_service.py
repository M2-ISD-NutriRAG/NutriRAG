from typing import Optional

from shared.snowflake.client import SnowflakeClient

from app.models.transform import TransformConstraints, TransformResponse


class TransformService:
    # Service de transformation de recettes

    async def transform(
        self,
        recipe_id: int,
        goal: str,
        constraints: Optional[TransformConstraints] = None,
    ) -> TransformResponse:
        # Transformer une recette en fonction de l'objectif et des contraintes
        # TODO: Équipe 3 - Implémentation de la logique de transformation
        # client = SnowflakeClient()

        raise NotImplementedError(
            "Équipe 3: Implémentation nécessaire - Logique de transformation"
        )
