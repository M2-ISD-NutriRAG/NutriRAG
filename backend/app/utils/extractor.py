import re
from typing import Dict, Any, Optional, Tuple
from app.models.transform import TransformConstraints


def extract_search_filters(query: str, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extrait des filtres structurés à partir :
    - de la requête utilisateur (texte libre)
    - du profil utilisateur (contraintes persistantes)
    Retourne un dict compatible avec SearchService.search(filters=...).
    """
    # TODO: Équipe 5 - Implémentation l'extraction des filtres a partir de la query avec un LLM ?

    filters: Dict[str, Any] = {}
    query = query.lower()

    # "moins de 500 calories", "max 600 kcal", "sous 400 cal"
    match_max_cal = re.search(r"(?:moins de|max|sous)\s*(\d+)\s*(?:k?cal|calories?)", query)
    if match_max_cal:
        filters["calories_max"] = int(match_max_cal.group(1))
    match_min_cal = re.search(r"(?:plus de|min|au moins)\s*(\d+)\s*(?:k?cal|calories?)", query)
    if match_min_cal:
        filters["calories_min"] = int(match_min_cal.group(1))

    # PROTÉINES
    if any(expr in query for expr in ["riche en protéines", "riche en protéine", "protéiné", "high protein"]):
        filters.setdefault("protein_min", 25)
    match_protein = re.search(r"(?:plus de|au moins|min)\s*(\d+)\s*(?:g|grammes?)\s*(?:de)?\s*protéines?", query)
    if match_protein:
        filters["protein_min"] = int(match_protein.group(1))

    # GLUCIDES
    if any(expr in query for expr in ["pauvre en glucides", "low carb", "faible en glucides"]):
        filters.setdefault("carbs_max", 40)
    match_carbs = re.search(r"(?:moins de|max)\s*(\d+)\s*(?:g|grammes?)\s*(?:de)?\s*glucides?", query)
    if match_carbs:
        filters["carbs_max"] = int(match_carbs.group(1))

    # RÉGIMES ET TYPES
    if "végétarien" in query or "vegetarien" in query or "végé" in query:
        filters["vegetarian"] = True
    if "végane" in query or "vegan" in query:
        filters["vegan"] = True
    if "sans sucre" in query or "no sugar" in query:
        filters["no_sugar"] = True
    if "sans lactose" in query or "no lactose" in query:
        filters["no_lactose"] = True
    if "sans gluten" in query or "no gluten" in query:
        filters["no_gluten"] = True
    if "hallal" in query or "sans porc" in query or "no pig" in query:
        filters["hallal"] = True

    # PROFIL UTILISATEUR
    if user_profile:
        # Intolérances
        intolerances = user_profile.get("intolerances", []) or []
        if "lactose" in intolerances:
            filters["no_lactose"] = True
        if "gluten" in intolerances:
            filters["no_gluten"] = True

        # Régime utilisateur
        diet = user_profile.get("diet")
        if diet == "high_protein":
            filters.setdefault("protein_min", 25)
        elif diet == "low_carb":
            filters.setdefault("carbs_max", 40)
        elif diet == "keto":
            filters["keto"] = True
            filters.setdefault("carbs_max", 30)
        elif diet == "vegan":
            filters["vegan"] = True

        # Objectif
        goal = user_profile.get("goal")
        if goal == "weight_loss":
            filters.setdefault("calories_max", 500)
        elif goal == "muscle_gain":
            filters.setdefault("protein_min", 30)

        # Limite calorique personnalisée
        if "max_calories" in user_profile:
            filters.setdefault("calories_max", user_profile["max_calories"])

    return filters



def extract_transform_goal_and_constraints(query: str) -> Tuple[str, TransformConstraints]:
    """
    Analyse la requête utilisateur pour déterminer :
    - l'objectif de transformation (goal)
    - les contraintes (TransformConstraints)
    """
    q = query.lower()
    constraints = TransformConstraints()

    # Extraire l'objectif
    goal = "healthier"  # VALEUR PAR DEFAUT POUR LES TESTS
    if any(expr in q for expr in ["plus sain", "plus saine", "allège", "alléger", "allégée"]):
        goal = "healthier"
    if any(expr in q for expr in ["plus protéiné", "plus protéinée", "riche en protéines", "prise de masse"]):
        goal = "higher_protein"
        constraints.increase_protein = True
    if any(expr in q for expr in ["moins de glucides", "pauvre en glucides", "low carb"]):
        goal = "lower_carb"
        constraints.decrease_carbs = True

    # INTOLÉRANCES / RÉGIMES / ALLERGIES
    if "sans lactose" in q:
        constraints.no_lactose = True
    if "sans gluten" in q:
        constraints.no_gluten = True
    if "sans noix" in q or "sans arachides" in q or "sans fruits à coque" in q:
        constraints.no_nuts = True
    if "végétarien" in q or "vegetarien" in q:
        constraints.vegetarian = True
    if "végane" in q or "vegan" in q:
        constraints.vegan = True

    # moins de calories
    if any(expr in q for expr in ["moins calorique", "moins de calories", "allège en calories", "maigrir", "sèche"]):
        constraints.decrease_calories = True

    # moins de sel / sodium
    if any(expr in q for expr in ["moins salé", "moins de sel", "moins de sodium", "réduit en sel"]):
        constraints.decrease_sodium = True
    
    # moins de sucre
    if any(expr in q for expr in ["moins sucré", "moins de sucre", "less sugar", "decrease sugar", "réduit le sucre"]):
        constraints.decrease_sodium = True

    return goal, constraints