# NutriRAG

**Système intelligent de recherche et transformation de recettes nutritionnelles**

Projet Data & IA - Session 2025-2026 - Master ISD
Encadrant : M. Anthony Coutant

## Vue d'ensemble

NutriRAG est un assistant culinaire intelligent qui combine :
- **RAG (Retrieval-Augmented Generation)** pour la recherche sémantique de recettes
- **Transformation nutritionnelle** automatique pour adapter les recettes
- **Analytics ML** pour le clustering d'ingrédients et les insights
- **Orchestration multi-agents** pour gérer les requêtes complexes

### Stack Technique

- **Backend**: FastAPI + Python 3.11
- **Frontend**: React 18 + TypeScript + Vite + Shadcn/UI
- **Database**: Snowflake (Cortex AI, Vector Search)
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

- Python 3.11.x
- Node.js 20+
- Docker & Docker Compose
- Compte Snowflake

### Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd NutriRAG
```

2. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos credentials Snowflake
```

3. **Installer les dépendances**
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

4. **Configurer pre-commit (optionnel mais recommandé)**

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
