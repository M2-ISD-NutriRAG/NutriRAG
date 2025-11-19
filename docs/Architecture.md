# API CONTRACTS (SNOWFLAKE + BACKEND)

### 1) Data APIs (Équipe 1)

→ returns enriched data from Snowflake

### 2) Search APIs (Équipe 2)

→ query RAG/Search embeddings from Snowflake Cortex AI

### 3) Transform APIs (Équipe 3)

→ apply transformation logic (SP Snowflake)

### 4) Analytics APIs (Équipe 4)

→ KPIs, clusters…

### 5) Orchestration APIs (Équipe 5)

→ orchestrator → router multi-agents



# API CONTRACTS

## 1. API – Recipes (Équipe 1)

### GET /recipes/{id}

| Field | Type |
| --- | --- |
| id | number |
| name | string |
| ingredients_parsed | array<{quantity, unit, name}> |
| nutrition_detailed | object |
| steps | array |
| score_health | float |

→ backend call Snowflake:

```sql
SELECT *
FROM NutriRAG_Project.ENRICHED.recipes_detailed
WHERE id = :id;
```

### GET /recipes?skip=&limit=

Returns a list of 1K or 50K samples.

## 2. API – Search (Équipe 2)

### POST /search

Body:

```json
{
  "query": "vegetarian high protein",
  "filters": {
    "protein_min": 30,
    "carbs_max": 50,
    "calories_max": 400,
    ...
  }
}
```

Response:

```json
{
  "results": [
    {
      "id": 123,
      "name": "Veggie Power Bowl",
      "similarity": 0.91,
      "nutrition": {...}
    }
  ]
}
```

→ Backend call Snowflake UDF:

```sql
SELECT search_recipes(:query, :filters_json)
```

## 3. API – Transform (Équipe 3)

### POST /transform

Body:

```json
{
  "recipe_id": 123,
  "goal": "healthier",
  "constraints": {
    "no_lactose": true,
    "increase_protein": true,
    ...
  }
}
```

Response:

```json
{
  "original": {...},
  "transformed": {...},
  "delta": {
    "protein": 12.5,
    "calories": -102,
    "score_health": 0.22,
    ...
  }
}
```

→ Backend call SP:
```sql
CALL transform_recipe(:recipe_id, :goal, :constraints_json);
```

## 4. API – Analytics (Équipe 4)

### GET /analytics/clusters

→ clusters ingredients/recipes

### GET /analytics/kpi

Response:
```json
{
  "matching_rate": 0.87,
  "coverage": 0.78,
  "latency_avg": 245,
  ...
}
```

## 5. API – Orchestration (Équipe 5)

### POST /orchestrate

Body:

```json
{
  "user_query": "Recette low-carb avec poulet, puis version plus protéinée",
  "context": {}
}
```

Response:

```json
{
  "steps": [
    {"agent": "search", "result": {...}},
    {"agent": "transform", "result": {...}}
  ],
  "final": {...}
}
```

Orchestrator flow:

1. Intent detection (LLM or rule-based)
2. Call Equipe 2 search
3. Call Equipe 3 transform
4. Return final result


# MONOREPO (FastAPI + React + Snowflake)

```
nutrirag/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── recipes.py
│   │   │   ├── search.py
│   │   │   ├── transform.py
│   │   │   ├── analytics.py
│   │   │   └── orchestration.py
│   │   ├── services/
│   │   │   ├── snowflake_client.py
│   │   │   ├── search_service.py
│   │   │   ├── transform_service.py
│   │   │   └── orchestrator.py
│   │   ├── models/
│   │   └── utils/
│   ├── requirements.txt
│   ├── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   │   ├── search.service.ts
│   │   │   ├── recipes.service.ts
│   │   │   └── transform.service.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── shared/
│   ├── types/
│   │   ├── recipe.ts
│   │   ├── search.ts
│   │   ├── analytics.ts
│   └── utils/
│
├── docker-compose.yml
└── README.md

```