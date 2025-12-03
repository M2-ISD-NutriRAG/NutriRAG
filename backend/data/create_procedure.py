import os
from typing import List
from shared.snowflake.client import SnowflakeClient


def run_remote_pipeline(session: Session,code: str,procedure_name: str = "RUN_EMBEDDING_PROCESS_SQL"):
    
    query = f"""
        CREATE OR REPLACE PROCEDURE {procedure_name}(
        MODEL_NAME STRING,
        TARGET_TABLE STRING,
        COLS ARRAY,
        SOURCE_TABLE STRING,
        DROP_TABLE BOOLEAN
    )
    RETURNS STRING
    LANGUAGE PYTHON
    RUNTIME_VERSION = '3.10'
    PACKAGES = ('snowflake-snowpark-python', 'pandas', 'sentence-transformers', 'filelock')
    EXTERNAL_ACCESS_INTEGRATIONS = (TRAINING_INTERNET_ACCESS)
    HANDLER = 'sp_handler'
    EXECUTE AS CALLER
    AS
    $$
    {code}
    $$
    """

    print("Exécution de la procédure stockée (cela peut prendre du temps)...")
    
    # 3. Exécution
    try:
        # .collect() force l'exécution immédiate
        result = session.sql(query).collect()
        print(f"Résultat : {result[0][0]}")
    except Exception as e:
        print(f"Erreur lors de l'appel à la procédure : {e}")
        raise e

def read_code():
    """Read all the code from the snowflake_procedure_table.py file."""
    file_path = os.path.join(os.path.dirname(__file__), "snowflake_procedure.py")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # Récupération de la session via votre utilitaire
    session = SnowflakeClient().get_snowpark_session()
    code = read_code()
    procedure_name = "RUN_EMBEDDING_PROCESS_SQL"
    try:
        run_remote_pipeline(session, code, procedure_name)
    finally:
        session.close()