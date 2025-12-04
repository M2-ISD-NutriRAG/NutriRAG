import os
# Assure-toi que cet import correspond à ta structure de projet
from shared.snowflake.client import SnowflakeClient 

def run_remote_pipeline(session , code: str, procedure_name: str = "RUN_EMBEDDING_PROCESS_WITH_CHUNKING"):
    
    query = f"""
        CREATE OR REPLACE PROCEDURE {procedure_name}(
            MODEL_NAME STRING,
            TARGET_TABLE STRING,
            METADATA_COLS ARRAY,      -- Anciennement COLS (ce qu'on colle au chunk)
            CHUNK_COL STRING,         -- NOUVEAU : La colonne à découper
            SOURCE_TABLE STRING,
            DROP_TABLE BOOLEAN,
            CHUNK_SIZE INT,           -- NOUVEAU : Taille max (ex: 512)
            CHUNK_OVERLAP INT         -- NOUVEAU : Chevauchement (ex: 64)
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

    print(f"Déploiement de la procédure {procedure_name} sur Snowflake...")
    
    try:
        # .collect() force l'exécution immédiate du CREATE PROCEDURE
        result = session.sql(query).collect()
        print(f"Succès : {result[0][0]}")
    except Exception as e:
        print(f"Erreur lors du déploiement : {e}")
        raise e

def read_code():
    """Lit le code Python qui contient la logique (sp_handler, imports, etc.)"""
    file_path = os.path.join(os.path.dirname(__file__), "snowflake_procedure.py")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # 1. Connexion
    client = SnowflakeClient()
    session = client.get_snowpark_session()
    
    try:
        # 2. Lecture du code Python (la logique V4 avec Chunking)
        code_logic = read_code()
        
        # 3. Déploiement de la Procédure Stockée
        proc_name = "RUN_EMBEDDING_PROCESS_WITH_CHUNKING"
        run_remote_pipeline(session, code_logic, proc_name)

        print("-" * 50)
        print(" Procédure déployée ! Tu peux maintenant l'appeler depuis Snowflake.")

    finally:
        session.close()