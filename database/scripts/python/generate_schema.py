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
except ImportError:
    # Fallback sur les variables d'environnement
    WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "NUTRIRAG_PROJECT")
    DATABASE = os.getenv("SNOWFLAKE_DATABASE", "NUTRIRAG_PROJECT")

# Lire le template SQL
template_path = Path(__file__).parent.parent / "sql" / "schema_db_template.sql"
with open(template_path, "r") as f:
    sql_template = f.read()

# Substituer les variables
sql_content = sql_template.replace("${WAREHOUSE_NAME}", WAREHOUSE)
sql_content = sql_content.replace("${DATABASE_NAME}", DATABASE)

# Afficher le SQL généré
print("=" * 80)
print(f"Création du schéma Snowflake")
print(f"WAREHOUSE: {WAREHOUSE}")
print(f"DATABASE: {DATABASE}")
print("=" * 80)
print(sql_content)
print("=" * 80)

# Optionnel: Sauvegarder dans un fichier
output_path = Path(__file__).parent.parent / "sql" / "schema_db_generated.sql"
with open(output_path, "w") as f:
    f.write(f"-- Auto-generated from schema_db_template.sql\n")
    f.write(f"-- WAREHOUSE: {WAREHOUSE}\n")
    f.write(f"-- DATABASE: {DATABASE}\n")
    f.write(f"-- Generated: {os.popen('date').read().strip()}\n\n")
    f.write(sql_content)

print(f"\n✅ Script SQL généré: {output_path}")
print("\nPour exécuter ce script dans Snowflake:")
print("1. Copiez le contenu ci-dessus")
print("2. Collez-le dans un worksheet Snowflake")
print("3. Ou utilisez snowsql: snowsql -f schema_db_generated.sql")
