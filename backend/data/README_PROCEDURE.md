# Guide Procédures Stockées Snowflake

## Qu'est-ce qu'une Procédure Stockée ?

Une **Procédure Stockée** est un script Python qui s'exécute directement dans Snowflake. Contrairement aux UDFs qui retournent une valeur pour chaque ligne, les procédures effectuent des traitements complexes (traiter des tables entières, générer des embeddings, etc.).

## Les 3 fichiers

1. **`snowflake_procedure.py`** - Contient ta logique Python (handler + code)
2. **`create_procedure.py`** - Crée la procédure dans Snowflake
3. **`launch_procedure.py`** - Exécute la procédure avec tes paramètres

## Étape 1 : Écrire ta procédure

Édite `snowflake_procedure.py` avec ta logique :

```python
def sp_handler(session, param1: str, param2: int):
    # Ta logique ici
    result = session.sql(f"SELECT * FROM MA_TABLE LIMIT {param2}").collect()
    return f"Traité {len(result)} lignes pour {param1}"
```

## Étape 2 : Créer la procédure dans Snowflake

```bash
python create_procedure.py
```

Le script :
- Lit automatiquement `snowflake_procedure.py`
- Crée une procédure nommée (défini dans le script)
- Déploie sur Snowflake

Par défaut : `RUN_EMBEDDING_PROCESS_WITH_CHUNKING`

## Étape 3 : Lancer la procédure

Édite `launch_procedure.py` pour configurer tes paramètres :

```python
# --- CONFIGURATION ---
SOURCE_TABLE = "MON_SCHEMA.MA_TABLE"
TARGET_TABLE = "MON_SCHEMA.RESULTAT"
MODEL = "all-MiniLM-L6-v2"
# ... autres paramètres
```

Puis lance :
```bash
python launch_procedure.py
```

## Exemple : Procédure d'embeddings

### Dans snowflake_procedure.py
```python
def sp_handler(session, model_name, target_table, source_table, chunk_size):
    # Charger le modèle
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    
    # Récupérer les données
    df = session.table(source_table).to_pandas()
    
    # Générer embeddings
    embeddings = model.encode(df['TEXT'].tolist())
    
    # Sauvegarder
    # ... logique de sauvegarde
    
    return f"Généré {len(embeddings)} embeddings"
```

### Créer
```bash
python create_procedure.py
```

### Lancer
Dans `launch_procedure.py` :
```python
SOURCE_TABLE = "NUTRIRAG_PROJECT.DEV_SAMPLE.RECIPES_SAMPLE_TINY"
TARGET_TABLE = "NUTRIRAG_PROJECT.DEV_SAMPLE.RECIPE_EMBEDDINGS"
MODEL = "all-MiniLM-L6-v2"
```

```bash
python launch_procedure.py
```

## Dans Snowflake

Tu peux aussi appeler la procédure directement :

```sql
CALL RUN_EMBEDDING_PROCESS_WITH_CHUNKING(
    'all-MiniLM-L6-v2',                    -- MODEL_NAME
    'TARGET_TABLE',                         -- TARGET_TABLE
    ARRAY_CONSTRUCT('NAME', 'TAGS'),       -- METADATA_COLS
    'DESCRIPTION',                          -- CHUNK_COL
    'SOURCE_TABLE',                         -- SOURCE_TABLE
    TRUE,                                   -- DROP_TABLE
    512,                                    -- CHUNK_SIZE
    64                                      -- CHUNK_OVERLAP
);
```

## Différence UDF vs Procédure

| Aspect | UDF | Procédure |
|--------|-----|-----------|
| **Usage** | `SELECT ma_udf(colonne)` | `CALL ma_procedure(params)` |
| **Retour** | Une valeur par ligne | Un message/statut |
| **Cas d'usage** | Transformer des valeurs | Traiter des lots de données |
| **Exemple** | Calculer, valider, nettoyer | Générer embeddings, ETL |

## Paramètres courants

### Pour embeddings avec chunking
- `MODEL_NAME` : Nom du modèle (ex: 'all-MiniLM-L6-v2')
- `SOURCE_TABLE` : Table source avec les textes
- `TARGET_TABLE` : Table de destination pour les embeddings
- `METADATA_COLS` : Colonnes à conserver (ARRAY)
- `CHUNK_COL` : Colonne à découper en morceaux
- `CHUNK_SIZE` : Taille max d'un chunk (ex: 512)
- `CHUNK_OVERLAP` : Chevauchement entre chunks (ex: 64)
- `DROP_TABLE` : Supprimer table existante (TRUE/FALSE)

## Tips

- Configure les paramètres dans `launch_procedure.py` avant de lancer
- Les packages nécessaires sont définis dans `create_procedure.py`
- N'oublie pas `EXTERNAL_ACCESS_INTEGRATIONS` pour accès internet
- Les procédures peuvent prendre du temps, sois patient
- Vérifie le résultat avec `SELECT * FROM table LIMIT 5`

## Packages communs

Dans `create_procedure.py`, ligne PACKAGES :
```python
PACKAGES = (
    'snowflake-snowpark-python',  # Obligatoire
    'pandas',                      # Pour DataFrames
    'sentence-transformers',       # Pour embeddings
    'filelock'                     # Pour sentence-transformers
)
```

## Accès externe

Pour télécharger des modèles, crée une intégration :
```sql
CREATE EXTERNAL ACCESS INTEGRATION TRAINING_INTERNET_ACCESS
    ALLOWED_NETWORK_RULES = (internet_access)
    ENABLED = TRUE;
```

Puis dans `create_procedure.py` :
```python
EXTERNAL_ACCESS_INTEGRATIONS = (TRAINING_INTERNET_ACCESS)
```
