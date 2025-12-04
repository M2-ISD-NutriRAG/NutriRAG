import sys
import os
import pandas as pd
import filelock
from snowflake.snowpark import Session
from snowflake.snowpark.types import PandasSeries

# --- 1. Génération de SQL de Nettoyage ---
def generate_metadata_sql(cols, type_map):
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

# --- 2. UDF d'Embedding ---
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
        max_batch_size=128 
    )
    return udf_name, dim

# --- 3. Handler Principal ---
def sp_handler(session: Session, embedding_model: str, target_table: str, metadata_cols: list, chunk_col: str, source_table: str, drop: bool, chunk_size: int, chunk_overlap: int):
    
    if not source_table: return "Erreur: Table source requise."

    try:
        desc_rows = session.sql(f"DESC TABLE {source_table}").collect()
        type_map = {row['name'].upper(): row['type'].upper() for row in desc_rows}
        source_cols_list = [f'"{row["name"]}"' for row in desc_rows if row["name"].upper() != 'EMBEDDING']
        cols_string = ", ".join(source_cols_list)
    except Exception as e:
        return f"Erreur inspection: {str(e)}"

    metadata_expr = generate_metadata_sql(metadata_cols, type_map)
    
    cortex_models = ["snowflake-arctic-embed-m", "snowflake-arctic-embed-l", "e5-base-v2"]
    if embedding_model in cortex_models:
        func = "EMBED_TEXT_1024" if "embed-l" in embedding_model else "EMBED_TEXT_768"
        select_embedding_sql = f"SNOWFLAKE.CORTEX.{func}('{embedding_model}', text_to_embed)"
    else:
        udf_name, dim = get_model_info_and_register_udf(session, embedding_model)
        select_embedding_sql = f"CAST({udf_name}(text_to_embed) AS VECTOR(FLOAT, {dim}))"

    # Vérifie bien que ce nom d'UDF est correct sur ton Snowflake
    chunk_udf_name = "NUTRIRAG_PROJECT.DEV_SAMPLE.CHUNK_TEXT_RECURSIVE_UDF"
    
    final_query_logic = f"""
    WITH PRE_PROCESSING AS (
        SELECT 
            {cols_string},
            {metadata_expr} AS METADATA_TEXT,
            {chunk_udf_name}({chunk_col}, {chunk_size}, {chunk_overlap}) AS CHUNKS_ARRAY
        FROM {source_table}
    ),
    FLATTENED_DATA AS (
        SELECT 
            P.* EXCLUDE (CHUNKS_ARRAY, METADATA_TEXT),
            F.INDEX AS CHUNK_INDEX,
            F.VALUE::STRING AS CHUNK_TEXT,
            METADATA_TEXT || ' ' || F.VALUE::STRING AS TEXT_TO_EMBED
        FROM PRE_PROCESSING P,
        LATERAL FLATTEN(input => P.CHUNKS_ARRAY) F
    )
    SELECT 
        *, 
        {select_embedding_sql} AS EMBEDDING
    FROM FLATTENED_DATA
    """

    if drop:
        ddl_query = f"CREATE OR REPLACE TABLE {target_table} AS {final_query_logic}"
    else:
        ddl_query = f"CREATE TABLE IF NOT EXISTS {target_table} AS {final_query_logic}"

    try:
        session.sql(ddl_query).collect()
    except Exception as e:
        return f"Erreur SQL: {str(e)}"

    return f"Succès : Table chunkée {target_table} créée."