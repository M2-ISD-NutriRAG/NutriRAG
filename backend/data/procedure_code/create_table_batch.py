import os
import math
from typing import List, Any, Optional, Iterator
from dotenv import load_dotenv
import pandas as pd

from snowflake.snowpark import Session, DataFrame
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import ArrayType, VariantType
from app.services.snowflake_client import get_snowflake_session

# Import local obligatoire pour MiniLM
try:
    from sentence_transformers import SentenceTransformer
    HAS_LOCAL_LIB = True
except ImportError:
    HAS_LOCAL_LIB = False

load_dotenv(override=True)

BATCH_SIZE = 1000  # Nombre de lignes par batch

def clean_cols(df: DataFrame, cols: List[str]) -> List[Any]:
    """Prépare les colonnes côté Snowflake avant téléchargement."""
    cleaned_exprs = []
    try:
        schema_dict = {f.name: f.datatype for f in df.schema.fields}
    except Exception:
        schema_dict = {}

    for c in cols:
        if schema_dict and c not in schema_dict:
            continue
        col_expr = F.col(c)
        dtype = schema_dict.get(c)

        if isinstance(dtype, ArrayType):
            col_expr = F.array_to_string(col_expr, F.lit(", "))
        elif isinstance(dtype, VariantType):
            col_expr = F.to_varchar(col_expr)
        else:
            col_expr = F.to_varchar(col_expr)

        cleaned = F.coalesce(F.trim(F.lower(col_expr)), F.lit(""))
        cleaned_exprs.append(cleaned)
    return cleaned_exprs

def merge_cols(cleaned_exprs: List[Any]) -> Any:
    return F.concat_ws(F.lit(" "), *cleaned_exprs)

def process_and_upload_batch(session: Session, 
                             batch_data: List[Any], 
                             model: Any, 
                             target_table: str, 
                             mode: str, 
                             dim: int):
    """
    Fonction helper qui traite un chunk pandas et l'envoie à Snowflake.
    """
    if not batch_data:
        return

    pdf = pd.DataFrame(batch_data)
    
    # show_progress_bar=False pour ne pas spammer la console à chaque batch
    embeddings = model.encode(pdf["TEXT_FOR_RAG"].tolist(), show_progress_bar=False)
    pdf["EMBEDDING"] = embeddings.tolist()
    
    # On supprime le texte temporaire pour ne pas stocker de duplicata (optionnel)
    pdf = pdf.drop(columns=["TEXT_FOR_RAG"])

    df_snow = session.create_dataframe(pdf)

    # C'est ici qu'on transforme l'Array Python en Type Vector Snowflake
    df_final = df_snow.with_column(
        "EMBEDDING", 
        F.sql_expr(f"CAST(EMBEDDING AS VECTOR(FLOAT, {dim}))")
    )
    
    # Écriture dans la table
    df_final.write.mode(mode).save_as_table(target_table)
    print(f"   -> Batch sauvegardé ({len(batch_data)} lignes).")


def run_batch_pipeline(session: Session, 
                       source_table: str, 
                       target_table: str, 
                       cols: List[str], 
                       model_name: str, 
                       drop: bool = False):
    
    if not HAS_LOCAL_LIB:
        raise ImportError("Vous avez besoin de 'sentence-transformers' pour utiliser MiniLM localement.")

    print(f"\n--- Démarrage Pipeline Batch ({source_table} -> {target_table}) ---")
    
    print(f"Chargement du modèle local '{model_name}'...")
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    print(f"Dimension vecteur : {dim}")

    if drop:
        print(f"Suppression de la table cible '{target_table}'...")
        session.sql(f"DROP TABLE IF EXISTS {target_table}").collect()
        write_mode = "overwrite" # Le premier batch crée la table
    else:
        write_mode = "append"

    df_source = session.table(source_table)
    cleaned_exprs = clean_cols(df_source, cols)
    concat_expr = merge_cols(cleaned_exprs)
    
    # On prépare la projection finale : Colonnes d'origine + Texte concaténé
    # On n'exécute PAS encore.
    df_prepared = df_source.with_column("TEXT_FOR_RAG", concat_expr)
    
    # to_local_iterator() télécharge les données flux par flux, sans saturer la RAM
    print("Récupération du stream de données...")
    iterator = df_prepared.to_local_iterator()

    batch_buffer = []
    total_processed = 0
    is_first_batch = True

    # 5. Boucle de Traitement
    for row in iterator:
        batch_buffer.append(row.as_dict())

        # Si le buffer est plein, on traite
        if len(batch_buffer) >= BATCH_SIZE:
            current_mode = "overwrite" if (is_first_batch and drop) else "append"
            
            print(f"Traitement batch {total_processed} à {total_processed + BATCH_SIZE}...")
            process_and_upload_batch(session, batch_buffer, model, target_table, current_mode, dim)
            
            # Reset
            batch_buffer = []
            total_processed += BATCH_SIZE
            is_first_batch = False # Les suivants seront toujours en append
            # Si on était en mode drop, maintenant la table existe, on passe en append
            if drop: drop = False 

    # 6. Traitement du reste (dernier buffer incomplet)
    if batch_buffer:
        current_mode = "overwrite" if (is_first_batch and drop) else "append"
        print(f"Traitement dernier batch ({len(batch_buffer)} lignes)...")
        process_and_upload_batch(session, batch_buffer, model, target_table, current_mode, dim)

    print("\n--- Terminé avec succès ---")


if __name__ == "__main__":
    session = get_snowflake_session()
    
    # Config
    SOURCE = "RECIPES_SAMPLE"
    TARGET = "RECIPE_EMBEDDINGS_BATCH"
    COLS = ["NAME", "DESCRIPTION", "INGREDIENTS", "STEPS", "TAGS"] 
    MODEL = "all-MiniLM-L6-v2" # 384 dims

    try:
        # On lance le pipeline par batch
        # drop=True signifie que le premier batch écrase la table, les suivants ajoutent à la suite
        run_batch_pipeline(session, SOURCE, TARGET, COLS, MODEL, drop=True)
        
        # Vérif
        print("\n--- Aperçu ---")
        session.table(TARGET).select("NAME", "EMBEDDING").show(2)

    finally:
        session.close()