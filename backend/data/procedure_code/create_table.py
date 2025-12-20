import os
import atexit
from dotenv import load_dotenv
from snowflake.snowpark import Session, DataFrame
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import ArrayType, VariantType
from typing import List, Any, Optional
from app.services.snowflake_client import get_snowflake_session

try:
    from sentence_transformers import SentenceTransformer
    HAS_LOCAL_LIB = True
except ImportError:
    HAS_LOCAL_LIB = False

load_dotenv(override=True)


def clean_cols(df: DataFrame, cols: List[str]) -> List[Any]:
    cleaned_exprs = []
    try:
        schema_dict = {f.name: f.datatype for f in df.schema.fields}
    except Exception:
        # Fallback si lecture schema impossible (ex: vue complexe)
        schema_dict = {}

    for c in cols:
        # Petite sécurité : Si on connait le schéma, on vérifie. Sinon on tente quand même.
        if schema_dict and c not in schema_dict:
            print(f" Colonne '{c}' absente. Ignorée.")
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


def embedd(session: Session, df: DataFrame, input_col_name: str, model_name: str) -> DataFrame:
    cortex_models = ["snowflake-arctic-embed-m", "snowflake-arctic-embed-l", "e5-base-v2"]
    
    # Détermination de la dimension du vecteur
    if "embed-l" in model_name: 
        dim = 1024
    elif model_name in cortex_models:
        dim = 768
    else: # Le modèle local standard fait 384
        model = SentenceTransformer(model_name)
        dim = model.get_sentence_embedding_dimension()

    # === OPTION A : Snowflake CORTEX ===
    if model_name in cortex_models:
        print(f" Calcul via Cortex ({model_name} - {dim}d)...")
        func_name = f"SNOWFLAKE.CORTEX.EMBED_TEXT_{dim}"
        
        # Cortex retourne déjà un VECTOR, mais c'est bien de s'assurer
        return df.with_column(
            "EMBEDDING", 
            F.call_builtin(func_name, model_name, F.col(input_col_name))
        )

    # === OPTION B : Modèle LOCAL ===
    else:
        print(f"Calcul Local ({model_name} - {dim}d)...")
        if not HAS_LOCAL_LIB:
            raise ImportError("Manque 'sentence_transformers'. pip install sentence-transformers")

        # Conversion Pandas pour calcul local
        try:
            pdf = df.to_pandas()
        except Exception as e:
            print("Erreur to_pandas(). Avez-vous installé: pip install \"snowflake-connector-python[pandas]\" pyarrow")
            raise e

        # Calcul des embeddings
        print("   -> Encodage en cours...")
        embeddings = model.encode(pdf[input_col_name].tolist(), show_progress_bar=True)
        pdf["EMBEDDING"] = embeddings.tolist()
        
        # Retour vers Snowpark
        df_snow = session.create_dataframe(pdf)
                
        print(f"   -> Conversion en format VECTOR({dim})...")

        # On injecte la syntaxe SQL native ::VECTOR(FLOAT, N)
        return df_snow.with_column(
            "EMBEDDING", 
            F.sql_expr(f"CAST(EMBEDDING AS VECTOR(FLOAT, {dim}))")
        )

def create_table(session: Session, 
                 embedding_model: str, 
                 target_table: str, 
                 cols_to_concat: List[str], 
                 source_table: Optional[str] = None, 
                 drop: bool = False):
    
    print(f"\nTraitement pour '{target_table}'...")
    source_df = None

    # Logique de récupération de la source (inchangée)
    try:
        temp_df = session.table(target_table)
        _ = temp_df.schema 
        print(f"Table cible existante.")
        if drop:
             if source_table:
                 print(f"   -> Mode Drop: Rechargement depuis '{source_table}'.")
                 source_df = session.table(source_table)
             else:
                 print(f"   -> Mode Drop: Réutilisation des données actuelles.")
                 source_df = temp_df
        else:
            print("   -> Mode Append.")
            source_df = temp_df
    except Exception:
        print(f"Table cible inexistante.")
        if source_table:
            print(f"   -> Création depuis '{source_table}'.")
            source_df = session.table(source_table)
        else:
            print("Erreur: Pas de source.")
            return

    # Pipeline
    print(f"Clean & Merge des colonnes : {cols_to_concat}")
    cleaned_exprs = clean_cols(source_df, cols_to_concat)
    if not cleaned_exprs: return

    concat_expr = merge_cols(cleaned_exprs)
    
    # On ajoute le texte temporaire
    df_prepared = source_df.with_column("TEXT_FOR_RAG", concat_expr)
    
    # On calcule l'embedding (qui ajoute la colonne EMBEDDING format VECTOR)
    df_final = embedd(session, df_prepared, "TEXT_FOR_RAG", embedding_model)
    
    # On supprime le texte temporaire (on garde juste les métadonnées + vecteur)
    df_final = df_final.drop("TEXT_FOR_RAG")

    mode = "overwrite" if drop else "append"
    print(f" Sauvegarde dans '{target_table}' (Mode: {mode})...")
    
    df_final.write.mode(mode).save_as_table(target_table)
    print("Terminé.")

# --- Main ---

def get_session():
    params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "authenticator": "Snowflake",
        "passcode": os.getenv("SNOWFLAKE_PASSCODE")
    }
    params = {k: v for k, v in params.items() if v}
    return Session.builder.configs(params).create()

if __name__ == "__main__":
    session = get_snowflake_session()
    
    target = "RECIPE_EMBEDDINGS_TEST"
    source = "RECIPES_SAMPLE"
    cols = ["NAME", "DESCRIPTION", "INGREDIENTS", "STEPS", "TAGS"] 
    
    # Choix modèle
    model = "all-MiniLM-L6-v2" # 384 dims
    #model = "e5-base-v2" # 768 dims

    try:
        create_table(session, model, target, cols, source, drop=True)
        
        # Vérification du type VECTOR
        print("\n--- Vérification du Schéma ---")
        for field in session.table(target).schema.fields:
            if field.name == "EMBEDDING":
                print(f"Colonne EMBEDDING : {field.datatype}") # Doit afficher VectorType(...)
        
        print("\n--- Aperçu ---")
        session.table(target).select("NAME", "EMBEDDING").show(2)

    finally:
        session.close()