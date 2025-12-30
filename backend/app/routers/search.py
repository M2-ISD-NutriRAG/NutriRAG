from fastapi import APIRouter, HTTPException
from time import time

from app.models.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()


@router.post("/", response_model=SearchResponse)
async def search_recipes(request: SearchRequest):
    try:
        results = await search_service.search(
            query=request.query, filters=request.filters, limit=request.limit
        )

        return SearchResponse(**results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
