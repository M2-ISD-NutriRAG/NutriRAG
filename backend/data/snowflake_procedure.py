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
        col_expr = f"ARRAY_TO_STRING({col_name}, ' ')" if 'ARRAY' in col_type else f"TO_VARCHAR({col_name})"
        cleaned_expr = f"COALESCE(TRIM(LOWER({col_expr})), '')"
        sql_parts.append(cleaned_expr)
    if not sql_parts: return "''"
    return " || ' ' || ".join(sql_parts)

# --- 2. UDF (Inchangée) ---
_cached_model = None
def get_model_info_and_register_udf(session, model_name):
    from sentence_transformers import SentenceTransformer
    cache_path = "/tmp/huggingface_cache"
    os.environ['HF_HOME'] = cache_path
    
    dim = 384
    try:
        lock_file = "/tmp/sp_model_load.lock"
        with filelock.FileLock(lock_file):
            temp_model = SentenceTransformer(model_name, cache_folder=cache_path)
            dim = temp_model.get_sentence_embedding_dimension()
            del temp_model
    except: pass 

    def run_embedding_batch(texts: PandasSeries[str]) -> PandasSeries[list]:
        global _cached_model 
        import os
        import filelock
        from sentence_transformers import SentenceTransformer
        
        if _cached_model is None:
            cache_path = "/tmp/huggingface_cache"
            os.environ['HF_HOME'] = cache_path
            lock_file = "/tmp/huggingface_worker.lock"
            with filelock.FileLock(lock_file):
                _cached_model = SentenceTransformer(model_name, cache_folder=cache_path)
        
        embeddings = _cached_model.encode(texts.tolist(), batch_size=32, show_progress_bar=False)
        return pd.Series(embeddings.tolist())

    udf_name = f"OPTIMIZED_EMBED_FUNC_{abs(hash(model_name))}"
    session.udf.register(
        run_embedding_batch, 
        name=udf_name, 
        is_permanent=False, 
        replace=True, 
        packages=["sentence-transformers", "pandas", "filelock"],
        external_access_integrations=["TRAINING_INTERNET_ACCESS"],
        max_batch_size=300 
    )
    return udf_name, dim

# --- 3. Handler Principal (CORRIGÉ POUR CLONAGE STRICT) ---
def sp_handler(session: Session, embedding_model: str, target_table: str, cols: list, source_table: str, drop: bool):
    
    if not source_table: return "Erreur: Table source requise."

    # A. Inspection stricte de la source
    try:
        desc_rows = session.sql(f"DESC TABLE {source_table}").collect()
        type_map = {row['name'].upper(): row['type'].upper() for row in desc_rows}
        
        # --- FIX : Liste explicite des colonnes (avec guillemets) ---
        # On exclut 'EMBEDDING' si elle existe déjà, car on va la recréer
        source_cols_list = [f'"{row["name"]}"' for row in desc_rows if row["name"].upper() != 'EMBEDDING']
        
    except Exception as e:
        return f"Erreur inspection: {str(e)}"

    concat_sql_expr = generate_cleaning_sql(cols, type_map)
    
    # B. Modèle
    cortex_models = ["snowflake-arctic-embed-m", "snowflake-arctic-embed-l", "e5-base-v2"]
    if embedding_model in cortex_models:
        method = "CORTEX"
        func = "EMBED_TEXT_1024" if "embed-l" in embedding_model else "EMBED_TEXT_768"
        select_embedding_sql = f"SNOWFLAKE.CORTEX.{func}('{embedding_model}', text_for_rag)"
    else:
        method = "LOCAL OPTIMIZED"
        udf_name, dim = get_model_info_and_register_udf(session, embedding_model)
        select_embedding_sql = f"CAST({udf_name}(text_for_rag) AS VECTOR(FLOAT, {dim}))"

    # C. Construction de la requête "SQL Strict"
    # On crée une chaine: "ID", "NAME", "TAGS" ...
    cols_string = ", ".join(source_cols_list)

    # Sous-requête (récupère tout + texte nettoyé)
    source_q = f"SELECT *, {concat_sql_expr} as text_for_rag FROM {source_table}"
    
    # Requête Finale
    # Au lieu de SELECT *, on fait SELECT colonnes_explicites
    if drop:
        final_query = f"""
            CREATE OR REPLACE TABLE {target_table} AS 
            SELECT {cols_string}, {select_embedding_sql} AS EMBEDDING 
            FROM ({source_q}) T
        """
    else:
        try:
             # Vérif si table existe
             session.sql(f"SELECT 1 FROM {target_table} LIMIT 1").collect()
             final_query = f"""
                INSERT INTO {target_table} ({cols_string}, EMBEDDING)
                SELECT {cols_string}, {select_embedding_sql} 
                FROM ({source_q}) T
             """
        except:
             final_query = f"""
                CREATE TABLE {target_table} AS 
                SELECT {cols_string}, {select_embedding_sql} AS EMBEDDING 
                FROM ({source_q}) T
             """

    session.sql(final_query).collect()
    return f"Succès V3 : Table {target_table} générée. Types préservés pour {len(source_cols_list)} colonnes."