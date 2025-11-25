from fastapi import APIRouter, HTTPException
from time import time

from app.models.orchestration import OrchestrationRequest, OrchestrationResponse
from app.services.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


@router.post("/", response_model=OrchestrationResponse)
async def orchestrate(request: OrchestrationRequest):
    
    # Point d'entrée de l'orchestrateur - routage des requêtes utilisateur vers les agents appropriés
    
    # Exemples:
    # - "Recette végétarienne riche en protéines" → Search agent
    # - "Rends cette recette plus saine" → Transform agent
    # - "Recette low-carb avec poulet, puis version plus protéinée" → Search + Transform
    
    start_time = time()
    
    try:
        # TODO: Équipe 5 - Implémentation de la logique d'orchestration
        # 1. Detect intent from user_query
        # 2. Route to appropriate agent(s)
        # 3. Handle sequential/parallel calls
        # 4. Manage context between steps

        result = await orchestrator.process(
            query=request.user_query,
            context=request.context,
            user_profile=request.user_profile
        )
        total_time = (time() - start_time) * 1000
        return OrchestrationResponse(
            steps=result["steps"],
            final_result=result["final"],
            intent_detected=result["intent"],
            total_execution_time_ms=total_time,
            success=result["success"]
        )
        
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="Équipe 5: Implémentation nécessaire - Détection d'intention + routage"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/intent")
async def detect_intent(user_query: str):
    # Détecter l'intention de l'utilisateur à partir de la requête sans exécuter
    # Retourne: search, transform, analytics, recipe_detail, multi_step
    # TODO: Équipe 5 - Implémentation de la logique de détection d'intention (LLM ou règles simples)
    
    raise HTTPException(
        status_code=501,
        detail="Équipe 5: Implémentation nécessaire - Détection d'intention"
    )


@router.get("/context/{session_id}")
async def get_context(session_id: str):
    # Obtenir le contexte de la conversation pour une session
    # TODO: Équipe 5 - Gestion des sessions/contexte

    raise HTTPException(
        status_code=501,
        detail="Équipe 5: Implémentation nécessaire - Gestion des sessions/contexte"
    )

