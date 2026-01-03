from fastapi import APIRouter, HTTPException
from time import time

from app.models.m_test import Response, Request
from app.services.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


@router.post("/", response_model=Response)
async def orchestrate(request: Request):
    
    # Point d'entrée de l'orchestrateur - routage des requêtes utilisateur vers les agents appropriés
    
    # Exemples:
    # - "Recette végétarienne riche en protéines" → Search agent
    # - "Rends cette recette plus saine" → Transform agent
    # - "Recette low-carb avec poulet, puis version plus protéinée" → Search + Transform

    print(f"Received orchestration request: {request}")

    return Response()  # Placeholder response