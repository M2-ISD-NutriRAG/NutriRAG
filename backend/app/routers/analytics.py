from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional
from json import loads
from app.models.analytics import (
    ClusterResponse,
    RecipeRanking,
    KPIResponse,
    TopIngredient,
    BiggestWin,
    ConversationStatsResponse,
    TransformationSummary,
)

router = APIRouter()


def get_db(
    request: Request,
):  # Dependency to get SnowflakeClient, from app main state
    return request.app.state.snowflake_client


@router.get("/clusters/ingredients", response_model=ClusterResponse)
async def get_ingredient_clusters(algorithm: Optional[str] = "kmeans"):
    # Obtenir les résultats du regroupement (clustering) des ingrédients
    # Retourne des clusters avec des étiquettes et des exemples
    # TODO: Équipe 4 - Retourner les clusters d'ingrédients de Snowflake

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Requête des clusters d'ingrédients",
    )


@router.get("/clusters/recipes", response_model=ClusterResponse)
async def get_recipe_clusters():
    # Obtenir les résultats du regroupement (clustering) des recettes (types de cuisine, catégories de plats)
    # TODO: Équipe 4 - Retourner les clusters de recettes

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Requête des clusters de recettes",
    )


@router.get("/kpi", response_model=KPIResponse)
async def get_kpis(
    user_id: Optional[str] = Query(
        None, description="L'ID de l'utilisateur pour filtrer les KPIs"
    ),
    db=Depends(get_db),
):
    """
    Récupère les KPI (Globaux ou pour un User spécifique).
    """
    try:
        session = db.get_snowpark_session()

        search_filter = ""
        trans_filter = ""
        params = []

        if user_id:
            search_filter = "WHERE USER_ID = ?"
            trans_filter = "AND USER_ID = ?"
            params = [user_id]

        # REQUÊTE 1 : METRIQUES DE VOLUME & NUTRITION (TRANSFORMATIONS)
        query_transforms_agg = f"""
            SELECT
                COUNT(*) as TOTAL_TRANSFORMS,
                SUM( (NUTRITION_BEFORE:calories::FLOAT) - (NUTRITION_AFTER:calories::FLOAT) ) as CALORIES_SAVED,
                SUM( (NUTRITION_AFTER:protein::FLOAT) - (NUTRITION_BEFORE:protein::FLOAT) ) as PROTEIN_GAINED,
                AVG( (NUTRITION_AFTER:score_health::FLOAT) - (NUTRITION_BEFORE:score_health::FLOAT) ) as AVG_HEALTH_GAIN,
                AVG( (ORIGINAL_RECIPE:minutes::INT) - (NEW_RECIPE:minutes::INT) ) as AVG_TIME_SAVED
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_TRANSFORMATIONS
            WHERE SUCCESS = TRUE
            {trans_filter}
        """

        res_agg = session.sql(
            query_transforms_agg, params=params if user_id else []
        ).collect()

        row_agg = res_agg[0]
        total_transforms = row_agg["TOTAL_TRANSFORMS"] or 0
        calories_saved = row_agg["CALORIES_SAVED"] or 0.0
        protein_gained = row_agg["PROTEIN_GAINED"] or 0.0
        avg_health_gain = row_agg["AVG_HEALTH_GAIN"] or 0.0
        avg_time_saved = row_agg["AVG_TIME_SAVED"] or 0.0

        # REQUÊTE 2 : VOLUME DE RECHERCHE & INGREDIENTS (SEARCH)
        query_search_stats = f"""
            SELECT
                COUNT(*) as CNT,
                AVG(MINUTES) as AVG_MINUTES  -- NOUVEAU
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH
            {search_filter}
        """
        res_search = session.sql(
            query_search_stats, params=params if user_id else []
        ).collect()
        total_searches = res_search[0]["CNT"] or 0
        avg_recipe_time = res_search[0]["AVG_MINUTES"] or 0.0

        # --- Analyse des ingrédients (Top 5 & Diversité) ---
        query_ingredients = f"""
            SELECT
                f.value::STRING as INGREDIENT_NAME,
                COUNT(*) as FREQUENCY
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH,
            LATERAL FLATTEN(input => RAW_RECIPE_JSON:ingredients) f
            {search_filter}
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 5
        """
        res_ingredients = session.sql(
            query_ingredients, params=params if user_id else []
        ).collect()

        top_ingredients_list = [
            TopIngredient(name=row["INGREDIENT_NAME"], count=row["FREQUENCY"])
            for row in res_ingredients
        ]

        # Diversité (Nombre total d'ingrédients uniques vus)
        query_diversity = f"""
            SELECT COUNT(DISTINCT f.value::STRING) as UNIQUE_COUNT
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH,
            LATERAL FLATTEN(input => RAW_RECIPE_JSON:ingredients) f
            {search_filter}
        """
        res_div = session.sql(
            query_diversity, params=params if user_id else []
        ).collect()
        diversity_index = res_div[0]["UNIQUE_COUNT"] or 0

        # REQUÊTE 3 : LA PLUS GROSSE OPTIMISATION (BIGGEST WIN)
        query_biggest_win = f"""
            SELECT
                ORIGINAL_NAME,
                TRANSFORMED_NAME,
                (NUTRITION_AFTER:score_health::FLOAT - NUTRITION_BEFORE:score_health::FLOAT) as DELTA_SCORE
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_TRANSFORMATIONS
            WHERE SUCCESS = TRUE AND DELTA_SCORE is not null
            {trans_filter}
            ORDER BY DELTA_SCORE DESC
            LIMIT 1
        """
        res_win = session.sql(
            query_biggest_win, params=params if user_id else []
        ).collect()

        biggest_win_obj = None
        if res_win and res_win[0]["DELTA_SCORE"] is not None:
            biggest_win_obj = BiggestWin(
                original_name=res_win[0]["ORIGINAL_NAME"],
                transformed_name=res_win[0]["TRANSFORMED_NAME"],
                health_score_delta=round(res_win[0]["DELTA_SCORE"], 2),
            )

        query_best = f"""
            SELECT DISTINCT NAME, SCORE_HEALTH
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH
            {search_filter} {("AND" if search_filter else "WHERE")} SCORE_HEALTH IS NOT NULL
            ORDER BY SCORE_HEALTH DESC
            LIMIT 5
        """
        res_best = session.sql(query_best, params=params).collect()
        top_healthy = [
            RecipeRanking(name=row["NAME"], health_score=row["SCORE_HEALTH"])
            for row in res_best
        ]

        query_worst = f"""
            SELECT DISTINCT NAME, SCORE_HEALTH
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH
            {search_filter} {("AND" if search_filter else "WHERE")} SCORE_HEALTH IS NOT NULL
            ORDER BY SCORE_HEALTH ASC
            LIMIT 5
        """
        res_worst = session.sql(query_worst, params=params).collect()
        top_unhealthy = [
            RecipeRanking(name=row["NAME"], health_score=row["SCORE_HEALTH"])
            for row in res_worst
        ]

        conversion_rate = 0.0
        if total_searches > 0:
            conversion_rate = round(
                (total_transforms / total_searches) * 100, 2
            )

        return KPIResponse(
            total_searches=total_searches,
            total_transformations=total_transforms,
            conversion_rate=conversion_rate,
            total_calories_saved=round(calories_saved, 1),
            total_protein_gained=round(protein_gained, 1),
            avg_health_score_gain=round(avg_health_gain, 2),
            ingredient_diversity_index=diversity_index,
            top_ingredients=top_ingredients_list,
            biggest_optimization=biggest_win_obj,
            top_5_healthy_recipes=top_healthy,
            top_5_unhealthy_recipes=top_unhealthy,
            avg_recipe_time=round(avg_recipe_time, 0),
            avg_time_saved=round(avg_time_saved, 1),
        )

    except Exception as e:
        print(f"Error fetching enriched KPIs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error during analytics processing",
        )


@router.get(
    "/conversation/{conversation_id}", response_model=ConversationStatsResponse
)
async def get_conversation_stats(conversation_id: str, db=Depends(get_db)):
    try:
        session = db.get_snowpark_session()

        # 1. Compter les messages
        query_search = "SELECT COUNT(*) as CNT FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH WHERE CONVERSATION_ID = ?"
        res_search = session.sql(
            query_search, params=[conversation_id]
        ).collect()
        total_messages = res_search[0]["CNT"] if res_search else 0

        # 2. Récupérer les JSONs pour calcul
        query_trans = """
            SELECT
                ORIGINAL_NAME,
                TRANSFORMED_NAME,
                NUTRITION_BEFORE,
                NUTRITION_AFTER
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_TRANSFORMATIONS
            WHERE CONVERSATION_ID = ? AND SUCCESS = TRUE
        """
        res_trans = session.sql(query_trans, params=[conversation_id]).collect()

        transformations = []

        for row in res_trans:
            bef = row["NUTRITION_BEFORE"]
            aft = row["NUTRITION_AFTER"]

            if isinstance(bef, str):
                bef = loads(bef)
            if isinstance(aft, str):
                aft = loads(aft)

            def get_val(data, key):
                return float(data.get(key, 0.0))

            # Calcul des Deltas (APRÈS - AVANT)
            transformations.append(
                TransformationSummary(
                    original_name=row["ORIGINAL_NAME"],
                    transformed_name=row["TRANSFORMED_NAME"],
                    delta_calories=round(
                        get_val(aft, "calories") - get_val(bef, "calories"), 2
                    ),
                    delta_protein=round(
                        get_val(aft, "protein") - get_val(bef, "protein_g"), 2
                    ),
                    delta_fat=round(
                        get_val(aft, "fat") - get_val(bef, "fat_g"), 2
                    ),
                    delta_carbs=round(
                        get_val(aft, "carbs") - get_val(bef, "carb_g"), 2
                    ),
                    delta_fiber=round(
                        get_val(aft, "fiber") - get_val(bef, "fiber_g"), 2
                    ),
                    delta_sugar=round(
                        get_val(aft, "sugar") - get_val(bef, "sugar_g"), 2
                    ),
                    delta_sodium=round(
                        get_val(aft, "sodium") - get_val(bef, "sodium_mg"), 2
                    ),
                    delta_health_score=round(
                        get_val(aft, "score_health")
                        - get_val(bef, "score_health"),
                        2,
                    ),
                )
            )

        return ConversationStatsResponse(
            total_messages=total_messages,
            total_transformations=len(transformations),
            transformations_list=transformations,
        )

    except Exception as e:
        print(f"Error fetching conversation stats: {e}")
        return ConversationStatsResponse(
            total_messages=0, total_transformations=0, transformations_list=[]
        )


@router.get("/distributions/{metric}")
async def get_distribution(metric: str):
    # Obtenir la distribution d'une mesure nutritionnelle sur les recettes
    # Mesures: calories, protein, carbs, fat, score_health
    # TODO: Équipe 4 - Retourner les données de l'histogramme/distribution

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Calculer les distributions",
    )


@router.get("/correlations")
async def get_correlations():
    # Obtenir la matrice de corrélation entre les mesures nutritionnelles et les évaluations
    # TODO: Équipe 4 - Calculer les corrélations

    raise HTTPException(
        status_code=501,
        detail="Équipe 4: Implémentation nécessaire - Analyse de corrélation",
    )
