from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional

from app.models.analytics import (
    ClusterResponse,
    KPIResponse,
    TopIngredient,
    BiggestWin,
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

        if user_id:
            search_filter = "WHERE USER_ID = ?"
            trans_filter = "AND USER_ID = ?"

        # REQUÊTE 1 : METRIQUES DE VOLUME & NUTRITION (TRANSFORMATIONS)
        query_transforms_agg = f"""
            SELECT
                COUNT(*) as TOTAL_TRANSFORMS,
                SUM(
                    (NUTRITION_BEFORE:calories::FLOAT) - (NUTRITION_AFTER:calories::FLOAT)
                ) as CALORIES_SAVED,
                SUM(
                    (NUTRITION_AFTER:protein::FLOAT) - (NUTRITION_BEFORE:protein::FLOAT)
                ) as PROTEIN_GAINED,
                AVG(
                    (NUTRITION_AFTER:score_health::FLOAT) - (NUTRITION_BEFORE:score_health::FLOAT)
                ) as AVG_HEALTH_GAIN
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_TRANSFORMATIONS
            WHERE SUCCESS = TRUE
            {trans_filter}
        """

        res_agg = session.sql(
            query_transforms_agg, params=[user_id] if user_id else []
        ).collect()

        row_agg = res_agg[0]
        total_transforms = row_agg["TOTAL_TRANSFORMS"] or 0
        calories_saved = row_agg["CALORIES_SAVED"] or 0.0
        protein_gained = row_agg["PROTEIN_GAINED"] or 0.0
        avg_health_gain = row_agg["AVG_HEALTH_GAIN"] or 0.0

        # REQUÊTE 2 : VOLUME DE RECHERCHE & INGREDIENTS (SEARCH)

        query_search_count = f"SELECT COUNT(*) as CNT FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH {search_filter}"
        res_search = session.sql(
            query_search_count, params=[user_id] if user_id else []
        ).collect()
        total_searches = res_search[0]["CNT"] or 0

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
            query_ingredients, params=[user_id] if user_id else []
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
            query_diversity, params=[user_id] if user_id else []
        ).collect()
        diversity_index = res_div[0]["UNIQUE_COUNT"] or 0

        # REQUÊTE 3 : LA PLUS GROSSE OPTIMISATION (BIGGEST WIN)
        query_biggest_win = f"""
            SELECT
                ORIGINAL_NAME,
                TRANSFORMED_NAME,
                (NUTRITION_AFTER:score_health::FLOAT - NUTRITION_BEFORE:score_health::FLOAT) as DELTA_SCORE
            FROM NUTRIRAG_PROJECT.ANALYTICS.HIST_TRANSFORMATIONS
            WHERE SUCCESS = TRUE
            {trans_filter}
            ORDER BY DELTA_SCORE DESC
            LIMIT 1
        """
        res_win = session.sql(
            query_biggest_win, params=[user_id] if user_id else []
        ).collect()

        biggest_win_obj = None
        if res_win and res_win[0]["DELTA_SCORE"] is not None:
            biggest_win_obj = BiggestWin(
                original_name=res_win[0]["ORIGINAL_NAME"],
                transformed_name=res_win[0]["TRANSFORMED_NAME"],
                health_score_delta=round(res_win[0]["DELTA_SCORE"], 1),
            )

        conversion_rate = 0.0
        if total_searches > 0:
            conversion_rate = round(
                (total_transforms / total_searches) * 100, 2
            )

        top_constraint = (
            "High Protein" if protein_gained > 50 else "Low Calorie"
        )

        return KPIResponse(
            total_searches=total_searches,
            total_transformations=total_transforms,
            conversion_rate=conversion_rate,
            total_calories_saved=round(calories_saved, 1),
            total_protein_gained=round(protein_gained, 1),
            avg_health_score_gain=round(avg_health_gain, 1),
            ingredient_diversity_index=diversity_index,
            top_ingredients=top_ingredients_list,
            biggest_optimization=biggest_win_obj,
            top_diet_constraint=top_constraint,
        )

    except Exception as e:
        print(f"Error fetching enriched KPIs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error during analytics processing",
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
