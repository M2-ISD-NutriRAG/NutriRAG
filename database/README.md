# Database - NutriRAG Data Pipeline

Ce dossier contient les scripts de setup initial et de gestion du schéma Snowflake pour le projet NutriRAG.


## 📁 Structure du dossier

```
database/
├── README.md                      # Ce fichier
├── scripts/
│   ├── python/                   # Scripts Python du pipeline
│   │   ├── main.py              # Orchestrateur principal
│   │   ├── PipelineOrchestrator.py
│   │   ├── SnowflakeUtils.py
│   │   ├── DataTransformer.py
│   │   ├── CleanData.py
│   │   ├── config.py
│   │   └── generate_schema.py
│   ├── sql/                      # Scripts SQL
│   │   ├── schema_db_template.sql
│   │   ├── schema_db_generated.sql
│   │   ├── ingest_clean_recipes.sql
│   │   ├── nutri_score.sql
│   └── └── extract_filters_udf.sql
└── (voir aussi /dataset/ pour les CSVs)
```

## 🔗 Modules liés

Ce dossier fait partie d'un écosystème plus large :

- **`/backend/shared/`** - Utilitaires partagés (client Snowflake, modèles d'embedding)
- **`/dataset/`** - Fichiers CSV nettoyés et clustering d'ingrédients

## 📝 Contenu des sous-dossiers

### `/scripts/python/` - Pipeline Python

Scripts d'orchestration du pipeline de données :

| Fichier | Description |
|---------|-------------|
| **main.py** | Point d'entrée principal - lance tout le pipeline de données |
| **PipelineOrchestrator.py** | Orchestre les phases du pipeline (setup, load, clean, ingest) |
| **SnowflakeUtils.py** | Gère la connexion à Snowflake (legacy - voir `/backend/shared/snowflake/`) |
| **DataTransformer.py** | Transforme et nettoie les données |
| **CleanData.py** | Ingère les données dans Snowflake |
| **generate_schema.py** | Génère le schéma SQL à partir du template |
| **config.py** | Configuration locale |

### `/scripts/sql/` - Schémas SQL

Scripts de création et configuration du schéma Snowflake :

| Fichier | Description |
|---------|-------------|
| **schema_db_template.sql** | Template du schéma (variables `${DATABASE_NAME}`, `${WAREHOUSE_NAME}`) |
| **schema_db_generated.sql** | Schéma généré avec les vraies valeurs |
| **ingest_clean_recipes.sql** | SQL pour ingérer et nettoyer les recettes |
| **nutri_score.sql** | Calcul du nutri-score |
| **extract_filters_udf.sql** | UDF pour extraire les filtres des recettes |

## 🚀 Démarrage rapide

### 1. Configuration Snowflake

Créez ou complétez un fichier `.env` à la racine du projet :

```bash
# Snowflake credentials
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_USER=your_username
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=NUTRIRAG_PROJECT
SNOWFLAKE_DATABASE=NUTRIRAG_PROJECT

```

### 2. Lancer le pipeline complet (optionnel)

```bash
# Pipeline complet (setup → load → clean → ingest)
python database/scripts/python/main.py
```

## 🎯 Commandes détaillées

Le script `main.py` supporte plusieurs options pour exécuter partiellement le pipeline :

### Pipeline complet
```bash
python database/scripts/python/main.py
```

### Phase 0 - Setup uniquement (créer le schéma)
```bash
python database/scripts/python/main.py --setup-only
```

### Phase 1 - Load uniquement (charger les données)
```bash
python database/scripts/python/main.py --load-only
```
## 🔄 Phases du pipeline

### Phase 0 : Setup Snowflake
1. Génère le schéma SQL depuis `schema_db_template.sql`
2. Crée les warehouses, databases et schemas
3. Crée les tables nécessaires

### Phase 1 : Load (Chargement)
1. Charge les données depuis les fichiers CSV locaux

## 📊 Structure du schéma Snowflake

Le schéma créé contient 4 schemas principaux :

| Schema | Contenu |
|--------|---------|
| **RAW** | Données brutes (non traitées) |
| **CLEANED** | Données nettoyées et validées |
| **DEV_SAMPLE** | Échantillon de développement (subset pour tests) |
| **ANALYTICS** | Tables analytiques et résumés |

### Tables principales

- `RECIPES_*` : Données des recettes
- `INGREDIENTS_*` : Données des ingrédients  
- `NUTRITION_*` : Données nutritionnelles
- `*_EMBEDDINGS` : Embeddings vectoriels (voir `/backend/data/embeddings/`)

## 📝 Logs

Les logs sont affichés en console et contiennent :
- Timestamp de chaque opération
- Niveau (INFO, WARNING, ERROR)
- Nom du module
- Message détaillé

Exemple :
```
2026-01-08 12:58:00 - PipelineOrchestrator - INFO - ✅ Phase 0: Schema setup completed
2026-01-08 12:59:00 - DataTransformer - INFO - Loaded 100000 recipes
```

## 💡 Conseils d'utilisation

- **Test** : Toujours tester avec `--nrows 10000` avant un pipeline complet
- **Schéma** : Utiliser `--setup-only` pour vérifier la configuration Snowflake
- **Logs** : Vérifier les logs pour identifier les étapes bloquantes
- **Performance** : La phase d'ingestion est la plus longue
- **Embeddings** : Utiliser `/backend/data/embeddings/` pour générer les embeddings vectoriels

## 🌐 Overview

Ce module fait partie du projet NutriRAG qui comprend :

- **Backend** (`/backend/`) - API FastAPI, services, modèles, data pipelines
- **Frontend** (`/frontend/`) - Interface React/TypeScript  
- **Database** (`/database/`) - Setup schéma et pipeline initial (ce module)

Voir le [README principal](/README.md) pour plus de détails sur l'architecture globale.

## 📚 Documentation liée

- [Backend Data README](/backend/data/embeddings/README.md) - Génération d'embeddings
- [Procédures Stockées](/backend/data/README_PROCEDURE.md) - Guide des procédures Snowflake
- [UDFs](/backend/data/README_UDF.md) - Guide des UDFs Snowflake
- [Modèles d'embedding](/backend/shared/models/README.md) - Modèles disponibles
- [Client Snowflake](/backend/shared/snowflake/README.md) - Documentation du client

## 👤 Support

Pour questions ou problèmes :
- Consulter les logs du pipeline
- Vérifier les docstrings des fichiers Python
- Voir la documentation des modules liés ci-dessus

