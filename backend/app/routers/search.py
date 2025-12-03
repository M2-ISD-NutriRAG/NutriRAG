from fastapi import APIRouter, HTTPException
from time import time

from app.models.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()


@router.post("/", response_model=SearchResponse)
async def search_recipes(request: SearchRequest):
    # Recherche sémantique avec filtres nutritionnels
    """
    Example:
    ```json
    {
      "query": "vegetarian high protein pasta",
      "filters": {
        "protein_min": 30,
        "carbs_max": 50,
        "calories_max": 400,
        ...
      },
      "limit": 10
    }
    ```
    """
    start_time = time()
    
    try:
        # TODO: Équipe 2 - Implement RAG search
        # ...
        
        results = await search_service.search(
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        
        execution_time = (time() - start_time) * 1000
        
        return SearchResponse(
            results=results,
            query=request.query,
            total_found=len(results),
            execution_time_ms=execution_time
        )
        
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Équipe 2: Implémentation nécessaire - RAG + recherche vectorielle + filtres"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/by-ingredients")
async def search_by_ingredients(ingredients: list[str], limit: int = 10):
    # Rechercher des recettes par ingrédients disponibles
    # Retourne les recettes qui peuvent être faites avec les ingrédients fournis,
    # plus des suggestions pour les ingrédients manquants.
    # TODO: Équipe 2 - Implémentation de la recherche par ingrédients

    raise HTTPException(
        status_code=501,
        detail="Équipe 2: Implémentation nécessaire - Recherche par ingrédients"
    )


@router.get("/similar/{recipe_id}")
async def find_similar_recipes(recipe_id: int, limit: int = 10):
    # Trouver des recettes similaires à une recette donnée
    # TODO: Équipe 2 - Utiliser l'embedding de la recette pour la recherche similaire

    raise HTTPException(
        status_code=501,
        detail="Équipe 2: Implémentation nécessaire - Recherche de recettes similaires"
    )

