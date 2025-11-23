from typing import List, Optional
from app.models.search import SearchFilters, SearchResult
from app.services.snowflake_client import get_snowflake_session


class SearchService:
    # Service de recherche utilisant Snowflake Cortex AI
    
    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        # Effectuer une recherche sémantique avec des filtres
        # TODO: Équipe 2 - Implémentation de la recherche sémantique avec des filtres
        # session = get_snowflake_session()
    
        # raise NotImplementedError("Équipe 2: Implémentation nécessaire - RAG + recherche vectorielle + filtres")
        # Faire un return static afin de tester seulement
        return [
            SearchResult(
                id=101,
                name="Poulet grillé aux légumes",
                description="Une recette saine, riche en protéines, idéale pour un repas équilibré.",
                similarity=0.91,
                nutrition={
                    "calories": 420,
                    "protein_g": 38,
                    "carbs_g": 22,
                    "fat_g": 14,
                    "fiber_g": 6
                },
                score_health=85.2,
                rating_avg=4.6,
                tags=["high_protein", "low_carb", "gluten_free"]
            ),
            SearchResult(
                id=202,
                name="Bowl quinoa & avocat",
                description="Un bowl végétarien nourrissant, riche en fibres et en bons lipides.",
                similarity=0.87,
                nutrition={
                    "calories": 390,
                    "protein_g": 18,
                    "carbs_g": 45,
                    "fat_g": 16,
                    "fiber_g": 9
                },
                score_health=78.4,
                rating_avg=4.3,
                tags=["vegetarian", "fiber_rich"]
            ),
            SearchResult(
                id=303,
                name="Saumon au four & brocoli",
                description="Délicieux saumon riche en oméga-3 accompagné de brocoli vapeur.",
                similarity=0.83,
                nutrition={
                    "calories": 450,
                    "protein_g": 34,
                    "carbs_g": 12,
                    "fat_g": 28,
                    "fiber_g": 5
                },
                score_health=88.1,
                rating_avg=4.8,
                tags=["omega_3", "keto_friendly", "high_protein"]
            )
        ][:limit]
    
