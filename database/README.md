# Database - NutriRAG Data Pipeline

Ce dossier contient tous les scripts pour la gestion de la base de données Snowflake du projet NutriRAG, incluant la création du schéma, le chargement des données, et leur transformation.

## 📁 Structure du dossier

```
database/
├── README.md                      # Ce fichier
├── requirements.txt               # Dépendances Python pour le pipeline
├── scripts/
│   ├── python/                   # Scripts Python pour le pipeline
│   └── sql/                      # Scripts SQL pour la création du schéma
└── dataset/                      # (Données locales, non versionné)
```

## 📝 Contenu des sous-dossiers

### `/scripts/python/` - Pipeline Python

Scripts d'orchestration du pipeline de données :

| Fichier | Description |
|---------|-------------|
| **main.py** | Point d'entrée principal - orchestre tout le pipeline |
| **PipelineOrchestrator.py** | Orchestre les phases du pipeline (setup, load, clean, ingest) |
| **SnowflakeConnector.py** | Gère la connexion à Snowflake |
| **DataLoader.py** | Charge les données depuis Google Drive et Kaggle |
| **DataTransformer.py** | Transforme et nettoie les données |
| **RecipeCleaner.py** | Spécifique au nettoyage des recettes |
| **IngredientParser.py** | Parse et traite les ingrédients |
| **SnowFlakeIngestor.py** | Ingère les données dans Snowflake |
| **SqlInsertGenerator.py** | Génère les requêtes SQL INSERT |
| **generate_schema.py** | Génère le schéma SQL à partir du template |
| **create_ingredients_quantities_csv.py** | Crée un CSV des quantités d'ingrédients |
| **config.py** | Configuration locale |
| **requirements.txt** | Dépendances Python |

### `/scripts/sql/` - Schémas SQL

Scripts de création et configuration du schéma Snowflake :

| Fichier | Description |
|---------|-------------|
| **schema_db_template.sql** | Template du schéma (variables `${DATABASE_NAME}`, `${WAREHOUSE_NAME}`) |
| **schema_db_generated.sql** | Schéma généré avec les vraies valeurs |
| **schema_db.sql** | Schéma statique (legacy) |
| **ingest_clean_recipes.sql** | SQL pour ingérer et nettoyer les recettes |
| **nutri_score.sql** | Calcul du nutri-score |
| **parse_quantity_udf.sql** | UDF Snowflake pour parser les quantités |

## 🚀 Démarrage rapide

### 1. Installation des dépendances

```bash
# Depuis la racine du projet
pip install -r database/requirements.txt
```

### 2. Configuration Snowflake

Créez ou complétez un fichier `.env` à la racine du projet :

```bash
# Snowflake credentials
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_USER=your_username
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=NUTRIRAG_PROJECT
SNOWFLAKE_DATABASE=NUTRIRAG_PROJECT

# Authentification par clé privée (recommandé)
SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/snowflake_key.pem
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=your_passphrase  # Optionnel

```

### 3. Lancer le pipeline complet

```bash
# Pipeline complet (setup → load → clean → ingest)
python database/scripts/python/main.py

# Avec un nombre limité de lignes (pour test)
python database/scripts/python/main.py --nrows 1000
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

### Phase 2 - Clean uniquement (nettoyer les données)
```bash
python database/scripts/python/main.py --clean-only
```

### Phase 3 - Ingest uniquement (insérer dans Snowflake)
```bash
python database/scripts/python/main.py --ingest-only
```

### Traiter uniquement les ingrédients
```bash
python database/scripts/python/main.py --process-ingredients
```

### Limiter à N lignes (test)
```bash
python database/scripts/python/main.py --nrows 500
```

## 🔄 Phases du pipeline

### Phase 0 : Setup Snowflake
1. Génère le schéma SQL depuis `schema_db_template.sql`
2. Crée les warehouses, databases et schemas
3. Crée les tables nécessaires

### Phase 1 : Load (Chargement)
1. Télécharge les données depuis les fichiers en local

### Phase 2 : Clean (Nettoyage)
1. Nettoie les recettes
2. Parse les ingrédients
3. Calcule les quantités
4. Valide les données

### Phase 3 : Ingest (Ingestion)
1. Ingère les données dans Snowflake
2. Valide l'intégrité

## 📊 Structure du schéma Snowflake

Le schéma créé contient 4 schemas principaux :

| Schema | Contenu |
|--------|---------|
| **RAW** | Données brutes (non traitées) |
| **CLEANED** | Données nettoyées et validées |
| **DEV_SAMPLE** | Échantillon de développement (moins de données) |
| **ANALYTICS** | Tables analytiques et résumés |

### Tables principales

- `RECIPES_*` : Données des recettes
- `INGREDIENTS_*` : Données des ingrédients
- `NUTRITION_*` : Données nutritionnelles
- `*_EMBEDDINGS` : Embeddings vectoriels


## 📝 Logs

Les logs sont affichés en console et contiennent :
- Timestamp de chaque opération
- Niveau (INFO, WARNING, ERROR)
- Nom du module
- Message détaillé

Exemple :
```
2026-01-03 12:58:00 - PipelineOrchestrator - INFO - ✅ Phase 0: Schema setup completed
2026-01-03 12:59:00 - DataLoader - INFO - Loaded 100000 recipes
```

## 💡 Conseils d'utilisation

- Toujours tester avec `--nrows 10000` avant un pipeline complet
- Utiliser `--setup-only` pour vérifier la configuration Snowflake
- Vérifier les logs pour identifier les étapes bloquantes
- La phase d'ingestion est la plus longue (peut prendre plusieurs minutes)
- Réutiliser les données téléchargées (elles sont cachées localement)

## 👤 Support

Pour questions ou problèmes, consulter :
- Les logs du pipeline
- Les docstrings des fichiers Python

