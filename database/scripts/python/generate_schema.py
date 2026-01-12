#!/usr/bin/env python3
"""
Script pour créer le schéma Snowflake avec des paramètres configurables.
Utilise les variables d'environnement ou le fichier config.py
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Importer la configuration
try:
    from config import SNOWFLAKE_CONFIG
    WAREHOUSE = SNOWFLAKE_CONFIG.get("warehouse", "NUTRIRAG_PROJECT")
    DATABASE = SNOWFLAKE_CONFIG.get("database", "NUTRIRAG_PROJECT")
    ROLE = SNOWFLAKE_CONFIG.get("role","TRAINING_ROLE")
except ImportError:
    # Fallback sur les variables d'environnement
    WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "NUTRIRAG_PROJECT")
    DATABASE = os.getenv("SNOWFLAKE_DATABASE", "NUTRIRAG_PROJECT")
    ROLE = os.getenv("SNOWFLAKE_ROLE","TRAINING_ROLE")


# Lire le template SQL
template_path = Path(__file__).parent.parent / "sql" / "schema_db_template.sql"
with open(template_path, "r") as f:
    sql_template = f.read()

# Substituer les variables
sql_content = sql_template.replace("${WAREHOUSE_NAME}", WAREHOUSE)
sql_content = sql_content.replace("${DATABASE_NAME}", DATABASE)
sql_content = sql_content.replace("${ROLE}", ROLE)



# Optionnel: Sauvegarder dans un fichier
output_path = Path(__file__).parent.parent / "sql" / "schema_db_generated.sql"
with open(output_path, "w") as f:
    f.write(f"-- Auto-generated from schema_db_template.sql\n")
    f.write(f"-- WAREHOUSE: {WAREHOUSE}\n")
    f.write(f"-- DATABASE: {DATABASE}\n")
    f.write(f"-- Generated: auto-generated schema\n\n")
    f.write(sql_content)

