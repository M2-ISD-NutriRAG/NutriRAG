USE
ROLE TRAINING_ROLE;
USE
WAREHOUSE NUTRIRAG_PROJECT;
USE
DATABASE NUTRIRAG_PROJECT;
USE
SCHEMA ANALYTICS;

CREATE OR REPLACE PROCEDURE NUTRIRAG_PROJECT.ANALYTICS.LOG_SEARCH_RECIPE("CONV_ID" VARCHAR, "USER_ID" VARCHAR, "FULL_RESPONSE" VARIANT)
RETURNS BOOLEAN
LANGUAGE SQL
EXECUTE AS OWNER
AS '
BEGIN
    INSERT INTO NUTRIRAG_PROJECT.ANALYTICS.HIST_SEARCH (
        CONVERSATION_ID,
        USER_ID,
        QUERY,
        TOTAL_FOUND,
        EXECUTION_TIME_MS,
        SEARCH_STATUS,
        RECIPE_ID,
        NAME,
        MINUTES,
        N_INGREDIENTS,
        N_STEPS,
        RATING_AVG,
        RATING_COUNT,
        CALORIES,
        PROTEIN_G,
        FAT_G,
        CARBS_G,
        SCORE_HEALTH,
        RAW_RECIPE_JSON
    )
    SELECT
        :CONV_ID,
        :USER_ID,
        :FULL_RESPONSE:query::STRING,
        :FULL_RESPONSE:total_found::INTEGER,
        :FULL_RESPONSE:execution_time_ms::FLOAT,
        :FULL_RESPONSE:status::STRING,
        r.value:id::INTEGER,
        r.value:name::STRING,
        r.value:minutes::INTEGER,
        r.value:n_ingredients::INTEGER,
        r.value:n_steps::INTEGER,
        r.value:rating_avg::FLOAT,
        r.value:rating_count::INTEGER,
        r.value:nutrition_detailed:energy_kcal_100g::FLOAT,
        r.value:nutrition_detailed:protein_g_100g::FLOAT,
        r.value:nutrition_detailed:fat_g_100g::FLOAT,
        r.value:nutrition_detailed:carbs_g_100g::FLOAT,
        r.value:score_sante::FLOAT,
        r.value
    FROM TABLE(FLATTEN(input => :FULL_RESPONSE:results)) r;

    RETURN TRUE;

EXCEPTION
    WHEN OTHER THEN
        RETURN FALSE;
END;
';
