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
