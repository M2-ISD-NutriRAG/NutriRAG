import os
from typing import List
from snowflake.snowpark import Session
# Assure-toi que cet import correspond à ton arborescence
from shared.snowflake.client import SnowflakeClient

def run_remote_pipeline(session: Session, 
                        model_name: str, 
                        target_table: str, 
                        metadata_cols: List[str], 
                        chunk_col: str,           
                        source_table: str, 
                        drop: bool = False,
                        chunk_size: int = 300,    
                        chunk_overlap: int = 64): 
    """
    Appelle la Procédure Stockée RUN_EMBEDDING_PROCESS_WITH_CHUNKING sur Snowflake.
    """
    print(f"\n Démarrage du pipeline de Chunking + Embedding...")
    print(f"Source: {source_table}")
    print(f"Cible : {target_table}")
    print(f"Modèle: {model_name}")
    print(f"Chunking sur colonne '{chunk_col}' (Size={chunk_size}, Overlap={chunk_overlap})")
    print(f"Métadonnées attachées : {metadata_cols}")

    # 1. Formatage de la liste Python pour le SQL Snowflake (ARRAY_CONSTRUCT)
    formatted_cols = ",".join([f"'{c}'" for c in metadata_cols])
    array_sql = f"ARRAY_CONSTRUCT({formatted_cols})"

    # 2. Gestion du booléen
    drop_sql = str(drop).upper()

    # 3. Construction de la requête SQL (Signature à 8 arguments)
    query = f"""
    CALL RUN_EMBEDDING_PROCESS_WITH_CHUNKING(
        '{model_name}',
        '{target_table}',
        {array_sql},
        '{chunk_col}',
        '{source_table}',
        {drop_sql},
        {chunk_size},
        {chunk_overlap}
    )
    """

    print("Exécution en cours sur Snowflake (patience)...")
    
    # 4. Exécution
    try:
        result = session.sql(query).collect()
        print(f"Résultat : {result[0][0]}")
    except Exception as e:
        print(f"Erreur lors de l'appel à la procédure : {e}")
        raise e

if __name__ == "__main__":
    # Récupération de la session
    session = SnowflakeClient().get_snowpark_session()
    
    # --- CONFIGURATION ---
    
    # Tables (Utilise tes tables réelles ou TINY pour tester)
    SOURCE_TABLE = "NUTRIRAG_PROJECT.DEV_SAMPLE.RECIPES_SAMPLE_TINY"
    # SOURCE_TABLE = "NUTRIRAG_PROJECT.CLEANED.RECIPES_SAMPLE_50K_STR"
    
    TARGET_TABLE = "NUTRIRAG_PROJECT.DEV_SAMPLE.RECIPE_CHUNKS_EMBEDDINGS_TEST"
    
    # Modèle
    MODEL = "all-MiniLM-L6-v2" 
    # MODEL = "e5-base-v2" 
    
    # Configuration du Chunking
    # 1. METADATA : Ce qu'on ne coupe pas mais qu'on colle devant chaque morceau
    METADATA_COLS = ["NAME", "TAGS"] 
    
    # 2. CHUNK_COL : Le gros texte à découper
    CHUNK_COL = "DESCRIPTION"
    
    # 3. Paramètres de découpe
    SIZE = 512
    OVERLAP = 64

    try:
        # Lancement du pipeline
        run_remote_pipeline(
            session=session, 
            model_name=MODEL, 
            target_table=TARGET_TABLE, 
            metadata_cols=METADATA_COLS, 
            chunk_col=CHUNK_COL, 
            source_table=SOURCE_TABLE, 
            drop=True,
            chunk_size=SIZE,
            chunk_overlap=OVERLAP
        )
        
        # Vérification rapide (Optionnel)
        print("\n--- Aperçu des 3 premières lignes générées ---")
        try:
            session.table(TARGET_TABLE).select("NAME", "CHUNK_INDEX", "CHUNK_TEXT", "EMBEDDING").show(3)
        except:
            print("Table non trouvée ou vide.")

    finally:
        session.close()