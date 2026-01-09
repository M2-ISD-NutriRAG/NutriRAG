-- Deployment script for GET_RECIPE_BY_ID
USE
ROLE TRAINING_ROLE;
USE
WAREHOUSE NUTRIRAG_PROJECT;
USE
DATABASE NUTRIRAG_PROJECT;
USE
SCHEMA SERVICES;

CREATE
OR REPLACE PROCEDURE SERVICES.GET_RECIPE_BY_ID(RECIPE_ID NUMBER)
RETURNS OBJECT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'get_recipe_by_id_handler'
EXECUTE AS CALLER
AS
$$
def get_recipe_by_id_handler(session, recipe_id: int):
    import time
    start_time = time.time()

    try:
        # Validate input
        try:
            recipe_id_int = int(recipe_id)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "recipe_id": recipe_id,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "recipe": None,
                "error": "recipe_id must be an integer",
            }

        # Query execution
        query = f"SELECT * FROM NUTRIRAG_PROJECT.ENRICHED.RECIPES_SAMPLE_50K WHERE ID = {recipe_id_int} LIMIT 1"
        rows = session.sql(query).collect()

        execution_time_ms = (time.time() - start_time) * 1000

        if not rows:
            return {
                "status": "not_found",
                "recipe_id": recipe_id_int,
                "execution_time_ms": execution_time_ms,
                "recipe": None,
            }

        row_dict = rows[0].as_dict()
        return {
            "status": "success",
            "recipe_id": recipe_id_int,
            "execution_time_ms": execution_time_ms,
            "recipe": row_dict,
        }

    except Exception as e:
        return {
            "status": "error",
            "recipe_id": recipe_id,
            "error": str(e),
            "execution_time_ms": (time.time() - start_time) * 1000,
        }
$$;