from typing import List, Optional

from shared.snowflake.client import SnowflakeClient

from app.models.search import SearchFilters, SearchResult


class SearchService:
    # Service de recherche utilisant Snowflake Cortex AI

    async def search(
        self, query: str, filters: Optional[SearchFilters] = None, limit: int = 10
    ) -> List[SearchResult]:
        # Effectuer une recherche sémantique avec des filtres
        # TODO: Équipe 2 - Implémentation de la recherche sémantique avec des filtres
        # client = SnowflakeClient()

        raise NotImplementedError(
            "Équipe 2: Implémentation nécessaire - RAG + recherche vectorielle + filtres"
        )
