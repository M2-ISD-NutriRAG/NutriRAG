import os
from typing import List
from snowflake.snowpark import Session
from shared.snowflake.client import SnowflakeClient


def run_remote_pipeline(session: Session, 
                        model_name: str, 
                        target_table: str, 
                        cols: List[str], 
                        source_table: str, 
                        drop: bool = False):
    """
    Appelle la Procédure Stockée RUN_EMBEDDING_PROCESS sur Snowflake.
    """
    print(f"\nDémarrage du pipeline distant sur Snowflake...")
    print(f"Source: {source_table} -> Cible: {target_table}")
    print(f"Modèle: {model_name}")

    # Formatage de la liste Python pour le SQL Snowflake
    # On transforme ['A', 'B'] en "'A','B'" pour le mettre dans ARRAY_CONSTRUCT
    formatted_cols = ",".join([f"'{c}'" for c in cols])
    array_sql = f"ARRAY_CONSTRUCT({formatted_cols})"

    # Construction de la requête SQL
    # Attention au booléen: Python 'True' devient SQL 'TRUE'
    drop_sql = str(drop).upper()

    query = f"""
    CALL RUN_EMBEDDING_PROCESS_SQL(
        '{model_name}',
        '{target_table}',
        {array_sql},
        '{source_table}',
        {drop_sql}
    )
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

if __name__ == "__main__":
    # Récupération de la session via votre utilitaire
    session = SnowflakeClient().get_snowpark_session()
    
    # Configuration
    TARGET = "RECIPE_EMBEDDINGS_TEST"
    SOURCE = "RECIPE_EMBEDDINGS" # Assurez-vous que c'est le bon nom de la table source
    COLS = ["NAME", "TAGS", "DESCRIPTION", "STEPS", "INGREDIENTS"] 
    
    # Choix du modèle (Cortex ou HuggingFace via l'intégration réseau)
    MODEL = "all-MiniLM-L6-v2" 
    # MODEL = "e5-base-v2" 

    try:
        # Lancement du pipeline distant
        run_remote_pipeline(session, MODEL, TARGET, COLS, SOURCE, drop=True)
        
        # Vérification des résultats
        print("\n--- Aperçu des données générées ---")
        session.table(TARGET).select("NAME", "EMBEDDING").show(2)

    finally:
        session.close()