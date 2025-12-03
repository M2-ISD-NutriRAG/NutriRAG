# API CONTRACTS (SNOWFLAKE + BACKEND)

### 1) Data APIs (Équipe 1)

→ returns enriched data from Snowflake

### 2) Search APIs (Équipe 2)

→ query RAG/Search embeddings from Snowflake Cortex AI

### 3) Transform APIs (Équipe 3)

→ This endpoint applies a nutritional or structural transformation to a recipe based on:
 - a transformation type (ADD, DELETE, SUBSTITUTION)
 - dietary or nutritional constraints
 - a recipe object provided by the client
 - goals such as increase protein, reduce carbs, etc.
→ This endpoint applies a nutritional or structural transformation to a recipe based on:
 - a transformation type (ADD, DELETE, SUBSTITUTION)
 - dietary or nutritional constraints
 - a recipe object provided by the client
 - goals such as increase protein, reduce carbs, etc.

### 4) Analytics APIs (Équipe 4)

→ KPIs, clusters…
KPIs : 
1. Average Health Score of Viewed Recipes
2. Average Protein per Recipe
3. Average Calories per Recipe
4. Top 5 Ingredients You Use the Most
5. Improvement from Transformations by timestamp
6. Average Prep Time
7. Average Macro Distribution
8. Average Calories Saved Thanks to Transformations
9. Most Frequent Substitutions

KPIs : 
1. Average Health Score of Viewed Recipes
2. Average Protein per Recipe
3. Average Calories per Recipe
4. Top 5 Ingredients You Use the Most
5. Improvement from Transformations by timestamp
6. Average Prep Time
7. Average Macro Distribution
8. Average Calories Saved Thanks to Transformations
9. Most Frequent Substitutions


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
  "k" : 5,
  "filers" : {
    "filtres_numeriques": [{
      "name" : "minute",
      "operator" : ">=",
      "value" : 30
    }, {
      "name" : "n_steps",
      "operator" : "<=",
      "value" : 15
    }, {
      "name" : "n_ingredients",
      "operator" : "=",
      "value" : 4
    }, {
      "name" : "servings",
      "operator" : ">=",
      "value" : 2
    }],
    "tags" : ["vegan", "low_carb", "hallal"...]
    "includes_ingredients" : ["chicken", "cheese"...]
    "exclude_ingredients" : ["fruits"]
  "k" : 5,
  "filers" : {
    "filtres_numeriques": [{
      "name" : "minute",
      "operator" : ">=",
      "value" : 30
    }, {
      "name" : "n_steps",
      "operator" : "<=",
      "value" : 15
    }, {
      "name" : "n_ingredients",
      "operator" : "=",
      "value" : 4
    }, {
      "name" : "servings",
      "operator" : ">=",
      "value" : 2
    }],
    "tags" : ["vegan", "low_carb", "hallal"...]
    "includes_ingredients" : ["chicken", "cheese"...]
    "exclude_ingredients" : ["fruits"]
  }
}
```

Response:

```json
{
  "results": [
    {
      "id": 101,
      "name": "High-Protein Veggie Bowl",
      "description": "A nutritious vegetarian bowl packed with plant-based protein.",
      "minutes": 25,
      "n_steps": 4,
      "n_ingredients": 7,
      "tags": ["vegetarian", "high_protein", "healthy"],
      "ingredients": [
        "Quinoa",
        "Chickpeas",
        "Avocado",
        "Spinach",
        "Olive oil",
        "Lemon",
        "Paprika"
      ],
      "steps": [
        "Cook the quinoa.",
        "Mix chickpeas with spices.",
        "Assemble the bowl with all ingredients.",
        "Add dressing and serve."
      ],
      "nutrition_detailed": {
        "calories": 480,
        "protein_g": 29,
        "carbs_g": 55,
        "fat_g": 18,
        "fiber_g": 11,
        "sodium_mg": 210
      },
      "score_health": 82.5,
      "rating_avg": 4.6,
      "rating_count": 214
      "id": 101,
      "name": "High-Protein Veggie Bowl",
      "description": "A nutritious vegetarian bowl packed with plant-based protein.",
      "minutes": 25,
      "n_steps": 4,
      "n_ingredients": 7,
      "tags": ["vegetarian", "high_protein", "healthy"],
      "ingredients": [
        "Quinoa",
        "Chickpeas",
        "Avocado",
        "Spinach",
        "Olive oil",
        "Lemon",
        "Paprika"
      ],
      "steps": [
        "Cook the quinoa.",
        "Mix chickpeas with spices.",
        "Assemble the bowl with all ingredients.",
        "Add dressing and serve."
      ],
      "nutrition_detailed": {
        "calories": 480,
        "protein_g": 29,
        "carbs_g": 55,
        "fat_g": 18,
        "fiber_g": 11,
        "sodium_mg": 210
      },
      "score_health": 82.5,
      "rating_avg": 4.6,
      "rating_count": 214
    }
  ],
  "query": "vegetarian high protein",
  "total_found": 1,
  "execution_time_ms": 12.47,
  "status": "success"
  ],
  "query": "vegetarian high protein",
  "total_found": 1,
  "execution_time_ms": 12.47,
  "status": "success"
}
```

→ Backend call Snowflake UDF:

```sql
SELECT search_recipes(:query, :filters_json)
```

## 3. API – Transform (Équipe 3)

### POST /transform

Cet endpoint applique une transformation nutritionnelle ou structurelle à une recette, selon :
 - un type de transformation (ADD, DELETE, SUBSTITUTION)
 - un ensemble de contraintes diététiques
 - un objectif nutritionnel (augmenter protéines, baisser sucre, etc.)
 - une recette complète envoyée par le client

Cet endpoint applique une transformation nutritionnelle ou structurelle à une recette, selon :
 - un type de transformation (ADD, DELETE, SUBSTITUTION)
 - un ensemble de contraintes diététiques
 - un objectif nutritionnel (augmenter protéines, baisser sucre, etc.)
 - une recette complète envoyée par le client

Body:

```json
{
  "recipe": {
    "name": "Creamy Pasta with Bacon",
    "ingredients": ["Pasta", "Heavy cream", "Bacon", "Salt"],
    "quantity_ingredients": ["200g", "100ml", "80g", "1 pinch"],
    "minutes": 25,
    "steps": [
      "Cook the pasta",
      "Sauté the bacon",
      "Add the cream and mix"
    ]
  },
  "recipe": {
    "name": "Creamy Pasta with Bacon",
    "ingredients": ["Pasta", "Heavy cream", "Bacon", "Salt"],
    "quantity_ingredients": ["200g", "100ml", "80g", "1 pinch"],
    "minutes": 25,
    "steps": [
      "Cook the pasta",
      "Sauté the bacon",
      "Add the cream and mix"
    ]
  },
  "constraints": {
    "transformation": "SUBSTITUTION",
    "transformation": "SUBSTITUTION",
    "no_lactose": true,
    "no_gluten": false,
    "no_nuts": false,
    "vegetarian": false,
    "vegan": false,

    "no_gluten": false,
    "no_nuts": false,
    "vegetarian": false,
    "vegan": false,

    "increase_protein": true,
    "decrease_sugar": false,
    "decrease_protein": false,
    "decrease_carbs": true,
    "decrease_calories": true,
    "decrease_sodium": true
    "decrease_sugar": false,
    "decrease_protein": false,
    "decrease_carbs": true,
    "decrease_calories": true,
    "decrease_sodium": true
  }
}
```

Response:

```json
{
  "recipe_id": 101,
  "original_name": "Creamy Pasta with Bacon",
  "transformed_name": "High-Protein Greek Yogurt Pasta with Turkey",

  "substitutions": [
    {
      "original_ingredient": "Heavy cream",
      "substitute_ingredient": "0% Greek yogurt",
      "original_quantity": 100.0,
      "substitute_quantity": 120.0,
      "reason": "Lower saturated fat, higher protein content"
    },
    {
      "original_ingredient": "Bacon",
      "substitute_ingredient": "Turkey breast",
      "original_quantity": 80.0,
      "substitute_quantity": 80.0,
      "reason": "Lower sodium and fat"
    }
  ],

  "nutrition_before": 42.0,
  "nutrition_after": 78.0,

  "recipe_id": 101,
  "original_name": "Creamy Pasta with Bacon",
  "transformed_name": "High-Protein Greek Yogurt Pasta with Turkey",

  "substitutions": [
    {
      "original_ingredient": "Heavy cream",
      "substitute_ingredient": "0% Greek yogurt",
      "original_quantity": 100.0,
      "substitute_quantity": 120.0,
      "reason": "Lower saturated fat, higher protein content"
    },
    {
      "original_ingredient": "Bacon",
      "substitute_ingredient": "Turkey breast",
      "original_quantity": 80.0,
      "substitute_quantity": 80.0,
      "reason": "Lower sodium and fat"
    }
  ],

  "nutrition_before": 42.0,
  "nutrition_after": 78.0,

  "delta": {
    "calories": -240.0,
    "protein_g": 20.0,
    "fat_g": -24.0,
    "carbs_g": -19.0,
    "fiber_g": 4.0,
    "sodium_mg": -470.0,
    "score_health": 36.0
  },

  "success": true,
  "message": "Transformation completed successfully using SUBSTITUTION rules."
    "calories": -240.0,
    "protein_g": 20.0,
    "fat_g": -24.0,
    "carbs_g": -19.0,
    "fiber_g": 4.0,
    "sodium_mg": -470.0,
    "score_health": 36.0
  },

  "success": true,
  "message": "Transformation completed successfully using SUBSTITUTION rules."
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
│   │   │   ├── UDF/
│   │   │   │   └── *.sql(or .py)
│   │   │   ├── snowflake_client.py
│   │   │   ├── search_service.py
│   │   │   ├── transform_service.py
│   │   │   └── orchestrator.py
│   │   ├── scripts/
│   │   │   └── agent_init.sql
│   │   ├── scripts/
│   │   │   └── agent_init.sql
│   │   ├── models/
│   │   └── utils/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── data/
│   │   └── *.csv
│   ├── tests/
│   ├── data/
│   │   └── *.csv
│   ├── tests/
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