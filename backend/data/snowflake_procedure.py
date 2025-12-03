import sys
import os
import pandas as pd
import filelock
from snowflake.snowpark import Session
from snowflake.snowpark.types import PandasSeries

# --- 1. Génération de SQL de Nettoyage ---
def generate_cleaning_sql(cols, type_map):
    sql_parts = []
    cols_upper = [c.upper() for c in cols]
    for col_name in cols_upper:
        if col_name not in type_map: continue
        col_type = type_map[col_name]
        
        if 'ARRAY' in col_type:
            col_expr = f"ARRAY_TO_STRING({col_name}, ' ')"
        elif 'VARIANT' in col_type:
            col_expr = f"TO_VARCHAR({col_name})"
        else:
            col_expr = f"TO_VARCHAR({col_name})"
            
        cleaned_expr = f"COALESCE(TRIM(LOWER({col_expr})), '')"
        sql_parts.append(cleaned_expr)
    
    if not sql_parts: return "''"
    return " || ' ' || ".join(sql_parts)

# --- 2. Gestion Modèle Local (Sentence Transformers) ---
def get_model_info_and_register_udf(session, model_name):
    from sentence_transformers import SentenceTransformer
    
    # Chemin de cache local (persistant tant que le Warehouse ne suspend pas)
    cache_path = "/tmp/huggingface_cache"
    os.environ['HF_HOME'] = cache_path
    os.environ['TRANSFORMERS_CACHE'] = cache_path
    
    lock_file = "/tmp/sp_model_load.lock"
    
    # A. Récupération de la dimension (Dynamique)
    # On télécharge/charge le modèle une fois ici pour avoir sa config
    dim = 384 
    try:
        with filelock.FileLock(lock_file):
            # Le cache_folder évite de retélécharger si déjà présent dans /tmp
            temp_model = SentenceTransformer(model_name, cache_folder=cache_path)
            dim = temp_model.get_sentence_embedding_dimension()
            del temp_model
    except Exception as e:
        raise Exception(f"Erreur chargement modèle local pour dimension: {str(e)}")

    # B. Définition de l'UDF Vectorisée
    # Cette fonction sera distribuée sur les nœuds workers
    def run_embedding_batch(texts: PandasSeries[str]) -> PandasSeries[list]:
        import os
        import filelock
        from sentence_transformers import SentenceTransformer
        
        # Réutilisation du même chemin de cache sur les workers
        cache_path = "/tmp/huggingface_cache"
        os.environ['HF_HOME'] = cache_path
        
        lock_file = "/tmp/huggingface_worker.lock"
        
        # Lock critique pour éviter que 8 threads téléchargent en même temps
        with filelock.FileLock(lock_file):
            model = SentenceTransformer(model_name, cache_folder=cache_path)
            
        embeddings = model.encode(texts.tolist(), show_progress_bar=False)
        return pd.Series(embeddings.tolist())

    udf_name = f"TEMP_EMBED_FUNC_{abs(hash(model_name))}"
    
    session.udf.register(
        run_embedding_batch, 
        name=udf_name, 
        is_permanent=False, 
        replace=True, 
        packages=["sentence-transformers", "pandas", "filelock"],
        external_access_integrations=["TRAINING_INTERNET_ACCESS"],
        max_batch_size=128
    )
    
    return udf_name, dim

# --- 3. Handler Principal ---
def sp_handler(session: Session, embedding_model: str, target_table: str, cols: list, source_table: str, drop: bool):
    
    if not source_table: return "Erreur: Table source requise."

    # A. Inspection de la table
    try:
        desc_rows = session.sql(f"DESC TABLE {source_table}").collect()
        type_map = {row['name'].upper(): row['type'].upper() for row in desc_rows}
    except Exception as e:
        return f"Erreur inspection table: {str(e)}"

    # B. Préparation du SQL de nettoyage
    concat_sql_expr = generate_cleaning_sql(cols, type_map)
    
    # C. Routage Modèle : Cortex vs Local
    # Liste des modèles supportés nativement par Snowflake (plus rapide/gratuit ou moins cher en calcul)
    cortex_models_supported = [
        "snowflake-arctic-embed-m", 
        "snowflake-arctic-embed-l", 
        "snowflake-arctic-embed-m-v1.5", 
        "e5-base-v2"
    ]
    
    select_embedding_sql = ""
    used_method = "UNKNOWN"

    # SI le modèle est dans Cortex -> On utilise la fonction native
    if embedding_model in cortex_models_supported:
        used_method = "CORTEX (Natif)"
        # Syntaxe unifiée Cortex (supporte e5-base-v2 maintenant)
        select_embedding_sql = f"SNOWFLAKE.CORTEX.EMBED_TEXT_768('{embedding_model}', text_for_rag)"
        
        # Exception pour Arctic Large qui est en 1024
        if 'arctic-embed-l' in embedding_model:
             select_embedding_sql = f"SNOWFLAKE.CORTEX.EMBED_TEXT_1024('{embedding_model}', text_for_rag)"
             
    # SINON -> On utilise la librairie Python locale (HuggingFace)
    else:
        used_method = f"LOCAL (Python UDF - Dim Auto)"
        try:
            udf_name, dim = get_model_info_and_register_udf(session, embedding_model)
            # Injection de la dimension dynamique ici
            select_embedding_sql = f"CAST({udf_name}(text_for_rag) AS VECTOR(FLOAT, {dim}))"
        except Exception as e:
            return f"Erreur configuration modèle local: {str(e)}"

    # D. Construction de la requête finale
    select_source_cols = "T.*"
    if "EMBEDDING" in type_map:
        select_source_cols = "T.* EXCLUDE (EMBEDDING)"

    source_query = f"SELECT *, {concat_sql_expr} as text_for_rag FROM {source_table}"
    
    if drop:
        final_query = f"""
        CREATE OR REPLACE TABLE {target_table} AS 
        SELECT {select_source_cols}, {select_embedding_sql} AS EMBEDDING
        FROM ({source_query}) T
        """
    else:
        # Gestion intelligente du Create if not exists vs Insert
        try:
            session.sql(f"SELECT 1 FROM {target_table} LIMIT 1").collect()
            final_query = f"""
            INSERT INTO {target_table}
            SELECT {select_source_cols}, {select_embedding_sql} AS EMBEDDING
            FROM ({source_query}) T
            """
        except:
            final_query = f"""
            CREATE TABLE {target_table} AS 
            SELECT {select_source_cols}, {select_embedding_sql} AS EMBEDDING
            FROM ({source_query}) T
            """

    # E. Exécution
    try:
        session.sql(final_query).collect()
    except Exception as e:
        return f"Erreur SQL Execution ({used_method}): {str(e)}"
    
    return f"Succès : {target_table} traité avec {embedding_model} via {used_method}."
