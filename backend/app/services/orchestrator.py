from typing import Dict, Any, Optional, List
from app.services.search_service import SearchService
from app.services.transform_service import TransformService
from app.utils.extractor import extract_search_filters, extract_transform_goal_and_constraints, split_into_subqueries
from time import time


class Orchestrator:
    # Logique principale d'orchestration
    
    def __init__(self):
        self.search_service = SearchService()
        self.transform_service = TransformService()
    
    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Process user query and route to appropriate agents
        # Returns:
        # {
        #     "intent": "search|transform|multi_step",
        #     "steps": [AgentStep, ...],
        #     "final": {...}
        # }
        # TODO: Équipe 5 - Implémentation de la logique d'orchestration
        
        # Step 1: Detect intent
        intent = await self._detect_intent(query, context)
        
        # Step 2: Route based on intent
        if intent == "search":
            return await self._handle_search(query, user_profile)
        elif intent == "transform":
            return await self._handle_transform(query, context)
        elif intent == "multi_step":
            return await self._handle_multi_step(query, context, user_profile)
        else:
            raise ValueError(f"Unknown intent: {intent}")
    
    async def _detect_intent(self, query: str, context: Optional[Dict]) -> str:
        # Détecter l'intention de l'utilisateur à partir de la requête
        
        # Options:
        # - LLM-based classification (Cortex.Complete)
        # - Rule-based (keywords)
        # - Hybrid
        
        # TODO: Équipe 5 - Détection d'intention
        # Simple rule-based pour le moment
        query_lower = query.lower()
        if any(word in query_lower for word in ["ensuite", "puis", "après"]):
            return "multi_step"
        elif any(word in query_lower for word in ["recherche", "trouve", "donne"]):
            return "search"
        elif any(word in query_lower for word in ["transforme", "rends", "plus sain"]):
            return "transform"
        return "UNDEFINED"  # Default
    
    async def _handle_search(self, query: str, user_profile: Optional[Dict]) -> Dict:
        # Gérer l'intention de recherche
        # TODO: Extract filters from query
        # Apply user_profile filters (intolerances, preferences)
        filters = extract_search_filters(query, user_profile)
        start_time = time()
        results = await self.search_service.search(
            query=query,
            filters=filters
        )
        execution_time_ms = (time() - start_time) * 1000
        return {
            "intent": "search",
            "steps": [{
                "agent": "search",                   
                "action": "semantic_search",
                "input": {
                    "query": query,
                    "filters": filters,
                    "limit": len(results)
                },
                "output": {
                    "results_count": len(results),
                },
                "success": True,
                "execution_time_ms": execution_time_ms
            }],
            "final": {
                "results": [r.dict() for r in results]
            },
            "success" : True
        }
    
    async def _handle_transform(self, query: str, context: Optional[Dict]) -> Dict:
        # Gérer l'intention de transformation
        # TODO: Get recipe_id from context
        # Extract goal from query
        recipe_id = None
        if context:
            # On accepte plusieurs clés possibles pour être robustes
            recipe_id = context.get("last_recipe_id") or context.get("recipe_id")
        # Si on trouve rien dans le contexte alors on renvoie rien
        if recipe_id is None:
            return {
                "intent": "transform",
                "steps": [],
                "final": {
                    "error": "Aucune recette cible trouvée dans le contexte pour la transformation."
                },
                "success": False
            }
        
        start_time = time()
        goal, constraints = extract_transform_goal_and_constraints(query)
        result = await self.transform_service.transform(
            recipe_id=recipe_id,
            goal=goal,
            constraints=constraints
        )
        execution_time_ms = (time() - start_time) * 1000

        return {
            "intent": "transform",
            "steps": [{
                "agent": "transform",
                "action": "transform_recipe",
                "input": {
                    "recipe_id": recipe_id,
                    "goal": goal,
                    "constraints": constraints.dict()
                },
                "output": {
                    "recipe_id": result.recipe_id,
                    "original_name": result.original_name,
                    "transformed_name": result.transformed_name,
                    "delta": result.delta.dict() if hasattr(result.delta, "dict") else result.delta,
                    "success": result.success,
                    "message": result.message,
                },
                "success": result.success,
                "execution_time_ms": execution_time_ms
            }],
            "final": result.dict() if hasattr(result, "dict") else result,
            "success" : True
        }

        # raise NotImplementedError("Équipe 5: Implémentation nécessaire - Gestion de l'intention de transformation")
    
    async def _handle_multi_step(
        self,
        query: str,
        context: Optional[Dict],
        user_profile: Optional[Dict]
    ) -> Dict:
        # Gérer les requêtes multi-étapes (appels d'agents séquentiels)
        # TODO: Décomposer la requête en étapes
        # Exécuter séquentiellement, en passant les résultats entre les étapes
        
        # raise NotImplementedError("Équipe 5: Implémentation nécessaire - Gestion des requêtes multi-étapes")

        if context is None:
            context = {}

        # Découper la requête globale en sous-requêtes
        # en splittant les query par puis|ensuite|et ensuite|et après
        subqueries = split_into_subqueries(query)

        all_steps: List[Dict[str, Any]] = []
        last_final: Optional[Dict[str, Any]] = None

        for sub_query in subqueries:
            result = await self.process(sub_query, context, user_profile)
            steps = result.get("steps", [])
            all_steps.extend(steps)
            if not result['success']:
                return {
                    "intent": "multi_step",
                    "steps": all_steps,
                    "final": {
                        "error": "Aucune recette cible trouvée dans le contexte pour la transformation."
                    },
                    "success": False,
                    "context": context,
                }
            last_final = result.get("final", last_final)
            # MAJ le contexte pour que les étapes suivantes puissent l'utiliser
            if result["intent"] == "search":
                final_results = (result["final"] or {})["results"] or []
                if final_results:
                    # On prend la première recette comme référence pour les étapes suivantes
                    # Peut etre qu'on peut trier par score de similarité et prendre la meilleure prochainement
                    first = final_results[0]
                    recipe_id = first["id"]
                    if recipe_id is not None:
                        context["last_recipe_id"] = recipe_id

            # On peut potentiellement mettre à jour le last_recipe_id avec la recette transformée
            if result["intent"] == "transform":
                transform_final = result["final"] or {}
                transformed_recipe_id = transform_final["recipe_id"]
                if transformed_recipe_id is not None:
                    context["last_recipe_id"] = transformed_recipe_id

        return {
            "intent": "multi_step",
            "steps": all_steps,
            "final": last_final,
            "success": True,
            "context": context,
        }


