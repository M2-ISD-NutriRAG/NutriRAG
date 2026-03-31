# NutriRAG

**Système intelligent de recherche et transformation de recettes nutritionnelles**

Projet Data & IA - Session 2025-2026 - Master ISD
Encadrant : M. Anthony Coutant

**Demo**: https://drive.google.com/file/d/1GlXLQwfc8T-9n_46arPhENhWDSeVD1kT/view?usp=sharing

## Vue d'ensemble

NutriRAG est un assistant culinaire intelligent qui combine :

- **RAG (Retrieval-Augmented Generation)** pour la recherche sémantique de recettes
- **Transformation nutritionnelle** automatique pour adapter les recettes
- **Analytics ML** pour le clustering d'ingrédients et les insights
- **Orchestration multi-agents** pour gérer les requêtes complexes

### Stack Technique

- **Backend**: FastAPI + Python 3.11
- **Frontend**: React 18 + TypeScript + Vite + Shadcn/UI
- **Database**: Snowflake (Cortex AI, Vector **Search**)
- **Deployment**: Docker + Docker Compose

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ÉQUIPE 5                             │
│              Orchestration & Interface                  │
│         (routage agents, contexte, profil user)         │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────┬───────────────┬─────────────┐
    │                 │               │             │
┌───▼─────┐      ┌────▼─────┐   ┌─────▼─────┐  ┌────▼────┐
│ Équipe 2│      │ Équipe 3 │   │ Équipe 4  │  │Équipe 1 │
│   RAG   │      │Transform │   │Analytics  │  │  Data   │
│ Search  │      │  Agents  │   │    ML     │  │ Enrich  │
└────┬────┘      └────┬─────┘   └────┬──────┘  └───┬─────┘
     │                │              │             │
     └────────────────┴──────────────┴─────────────┘
              BASE DE DONNÉES SNOWFLAKE
         (enrichie progressivement par Équipe 1)
```

## Quick Start

### Prérequis

- **Python 3.11.x**
- Node.js 20+
- Docker & Docker Compose
- Compte Snowflake
- **Git LFS** (pour gérer les fichiers volumineux)

### Configuration Git LFS

Ce projet utilise **Git LFS (Large File Storage)** pour gérer les fichiers volumineux (datasets, modèles, etc.). Vous DEVEZ installer et configurer Git LFS avant de cloner le repository.

**Installation de Git LFS :**

```bash
# macOS (avec Homebrew)
brew install git-lfs

# Ubuntu/Debian
sudo apt-get install git-lfs

# Windows (avec Chocolatey)
choco install git-lfs
```

**Configuration (à faire une seule fois) :**

```bash
# Configurer git lfs
git lfs install

# Cloner le repository (git lfs téléchargera automatiquement les fichiers)
git clone <repository-url>
cd NutriRAG
```

**Vérification :**

```bash
# Voir les fichiers gérés par git lfs
git lfs ls-files

# Vérifier que les fichiers sont bien téléchargés (pas des pointeurs)
file dataset/*.csv
```

Si vous clonez le repo SANS Git LFS configuré, vous aurez uniquement des pointeurs texte au lieu des vrais fichiers. Reconfigurer avec `git lfs install` et `git lfs pull` pour télécharger les vrais fichiers.

### Installation

1. **Cloner le repository**

```bash
git clone <repository-url>
cd NutriRAG
```

2. **Installer les dépendances**

```bash
# Backend
cd backend
python3.11 -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

3. **Configurer les variables d'environnement**

```bash
# Dans la racine du projet
cp .env.example .env
```

4. (Optionnel) Uniquement pour les personnes sur Windows

Vérifiez que `choco` est installé :

```Powershell
# Affiche la version de Chocolatey (si installé)
choco -v
```

(Optionnel) Si `choco` n'est pas installé, installez-le (administrateur terminal) :

```Powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Puis, installez OpenSSL (administrateur terminal) :

```Powershell
choco install openssl -y
```

**Relancez VSCode (avant de passer à la prochaine étape)**

5. **Configurer Snowflake avec authentification par clé RSA**

Pour se connecter à Snowflake de manière sécurisée, nous utilisons l'authentification par paire de clés RSA.

Lancez le script de configuration interactif :

```bash
cd backend
python setup_snowflake.py
```

- Utilisez **l'option 1** pour générer une nouvelle paire de clés RSA et configurer votre compte Snowflake **en suivant bien les étapes**.

- Utilisez **l'option 2 ou 3** pour tester la connexion.

**Note importante :** Pour toute question sur la configuration Snowflake ou les clés RSA, contactez **Mathusan**.

6. **Récupérer les identifiants (OAuth) dans Snowflake**
```sql
-- Get the Client Secret (This will give you a JSON blob containing the secret)
SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('MY_LOCALHOST_APP');
```
Le résultat s'affichera sous la forme d'un objet JSON :
```json
{
  "OAUTH_CLIENT_ID": "votre_client_id_ici...",
  "OAUTH_CLIENT_SECRET": "votre_secret_ici...",
  "OAUTH_CLIENT_SECRET_2": "..."
}
```
Copiez les valeurs de `OAUTH_CLIENT_ID` et `OAUTH_CLIENT_SECRET` dans le fichier `.env` aux variables `CLIENT_ID` et `CLIENT_SECRET`.

### Configurer pre-commit (optionnel mais recommandé)

Pre-commit permet d'exécuter automatiquement des vérifications de code (linting, formatage) avant chaque commit.

```bash
# Depuis la racine du projet, avec venv activé
pip install pre-commit
pre-commit install

# (Optionnel) Exécuter pre-commit sur tous les fichiers
pre-commit run --all-files
```

Les hooks configurés dans `.pre-commit-config.yaml` incluent :

**Hooks généraux :**

- **trailing-whitespace** : Supprime les espaces en fin de ligne
- **end-of-file-fixer** : Assure qu'il y a une ligne vide en fin de fichier
- **check-yaml** : Valide la syntaxe des fichiers YAML
- **check-json** : Valide la syntaxe des fichiers JSON
- **check-added-large-files** : Empêche l'ajout de gros fichiers

**Hooks Python :**

- **Ruff** : Linting Python (détection d'erreurs, respect des conventions)
- **Ruff Format** : Formatage automatique du code Python

Une fois installé, pre-commit s'exécutera automatiquement avant chaque `git commit` et bloquera le commit si des problèmes sont détectés.

**Corriger les erreurs détectées par pre-commit :**

Si pre-commit bloque votre commit à cause d'erreurs, voici les commandes pour les corriger :

```bash
# Pour les erreurs de linting Python (ruff) - corrige automatiquement ce qui peut l'être
ruff check --fix .

# Pour vérifier les erreurs Python restantes sans les corriger
ruff check .

# Pour formater le code Python manuellement
ruff format .

# Pour les erreurs de fichiers (espaces, fin de ligne, etc.) - relancer pre-commit
pre-commit run --all-files

# Après correction, recommencer le commit
git add .
git commit -m "votre message"
```

**Note :** La plupart des hooks généraux (trailing-whitespace, end-of-file-fixer) corrigent automatiquement les problèmes. Vous devrez simplement re-ajouter les fichiers modifiés avec `git add .` avant de recommiter.

### Développement

#### Option 1: Développement local

Terminal 1 - Backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:

```bash
cd frontend
npm run dev
```

Accéder à :

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

#### Option 2: Docker Compose

```bash
# Build et démarrer
docker-compose up --build
```

Accéder à :

- Frontend: http://localhost
- Backend API: http://localhost:8000

### Important !!!

- N'oubliez pas de configurer les variables d'environnement dans le fichier .env
- Il faut créer une nouvelle branche pour chaque équipe pour travailler sur le projet
- **Contactez Emmanuelle** pour toute question ou demande de support

## Structure du Projet et Contract API

[Architecture.md](./docs/Architecture.md)

## Testing

For information on how to write and run tests, see [Testing Guide](./backend/tests/README.md)

## Documentation Backend

### Modules Principaux

- **[Embeddings Pipeline](backend/data/embeddings/README.md)** - Création de tables Snowflake avec embeddings pour la recherche sémantique

  - Configuration des modèles d'embedding (Cortex vs local)
  - Modes de traitement (in-memory vs batch)
  - Guide de dépannage

- **[Snowflake Integration](backend/shared/snowflake/README.md)** - Client Snowflake et définitions de tables

  - Authentification (password vs key pair)
  - Schémas de tables (RecipesSampleTable, RecipesUnifiedEmbeddingsTable)

- **[Embedding Models](backend/shared/models/README.md)** - Modèles d'embedding disponibles
  - Modèles locaux (SentenceTransformers)
  - Modèles Snowflake Cortex

## Équipes & Responsabilités

### Équipe 1 : Data Foundation

- Tous les fichiers python de recettes (recipes...)

### Équipe 2 : RAG & Search Intelligence

- Tous les fichiers python de recherche (search...)

### Équipe 3 : Transformation & Agents

- Tous les fichiers python de transformation (transform...)

### Équipe 4 : Analytics & ML Insights

- Tous les fichiers python d'analytics (analytics...)
- Frontend de l'interface d'analytics (dashboard, ...)

### Équipe 5 : Orchestration & Interface

- Initialisation de l'architecture du projet
- Tous les fichiers python d'orchestration (orchestration...)
- Frontend de l'interface d'orchestration (chat page, ...)

## Datasets

### Food.com RAW_recipes (180K recettes)

- Colonnes: id, name, tags, ingredients, steps, nutrition, description
- Nutrition: [calories, fat, sugar, sodium, protein, sat_fat, carbs]

### cleaned_ingredients (~8K ingrédients)

- Profils nutritionnels détaillés par ingrédient
- Valeurs pour 100g

## License

Projet académique - Master ISD - Université Paris-Saclay

---

**Bon projet ! 🚀**
