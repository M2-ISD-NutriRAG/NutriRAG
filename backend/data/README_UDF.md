# Guide UDF Snowflake

## Qu'est-ce qu'une UDF ?

Une **UDF (User Defined Function)** est une fonction personnalisée que tu crées dans Snowflake. Tu peux l'appeler comme n'importe quelle fonction SQL.

## Les fichiers

1. **`snowflake_udf.py`** - Contient tes fonctions Python (exemples fournis)
2. **`create_udf.py`** - Crée la UDF dans Snowflake (mode intelligent)
3. **`launch_udf.py`** - Exécute une UDF déployée
4. **`udf.py`** - Script tout-en-un (créer OU lancer)

## Étape 1 : Écrire ta fonction

Édite `snowflake_udf.py` et ajoute ta fonction :

```python
def ma_fonction(param1: str) -> str:
    """Description de ma fonction"""
    return f"Hello {param1}!"
```

## Étape 2 : Créer la UDF dans Snowflake

```bash
cd backend
python -m data.create_udf
```

### Mode Analyse

Le script analyse automatiquement `snowflake_udf.py` et te propose les fonctions disponibles :

```
Fonctions disponibles:
1. udf_handler(name: str) -> str
   Simple Hello World UDF.

2. udf_square(x: float) -> float
   Calcule le carré d'un nombre.

3. udf_numpy_mean(numbers_json: str) -> float
   Calcule la moyenne avec numpy.
   📦 Packages: numpy
```

**Choisis simplement le numéro** et le script génère automatiquement :
- ✅ Les paramètres Snowflake (conversions Python → Snowflake)
- ✅ Le type de retour
- ✅ Les packages nécessaires (numpy, pandas, etc.)
- ✅ Le nom du handler

Ou tape **M** pour mode manuel.

## Étape 3 : Lancer ta UDF

```bash
cd backend
python -m data.launch_udf
```

Le script demande :
1. **Nom de l'UDF** (ex: `MY_UDF` ou `SCHEMA.MY_UDF`)
2. **Arguments** (un par ligne, ligne vide pour terminer)
3. Affiche le résultat

### Exemple d'utilisation
```
Nom de la UDF (ex: MY_UDF ou SCHEMA.MY_UDF)
UDF: DEV_SAMPLE.UDF_HANDLER

Entrez les arguments (un par ligne, ligne vide pour terminer):
Argument 1: Alice
Argument 2: 

EXÉCUTION DE LA UDF : DEV_SAMPLE.UDF_HANDLER
Requête SQL: SELECT DEV_SAMPLE.UDF_HANDLER('Alice')

RÉSULTAT
Hello World, Alice!
```

## Script tout-en-un

```bash
python -m data.udf
```

Menu interactif :
- **1** : Créer une UDF
- **2** : Lancer une UDF
- **3** : Quitter

## Exemples de fonctions

### Hello World
```python
def udf_handler(name: str) -> str:
    return f"Hello {name}!"
```

### Calcul simple
```python
def udf_square(x: float) -> float:
    return x ** 2
```

### Avec numpy
```python
def udf_numpy_mean(numbers_json: str) -> float:
    import numpy as np
    import json
    numbers = json.loads(numbers_json)
    return float(np.mean(numbers))
```
**Packages requis** : Ajoute `numpy` lors de la création

### Dans Snowflake
```sql
-- Utilisation directe
SELECT MY_UDF('test');

-- Sur une table
SELECT NAME, MY_UDF(NAME) AS RESULT
FROM MY_TABLE;
```

## Conversion automatique des types

| Python | Snowflake |
|--------|-----------|
| `str` | `STRING` |
| `int` | `INT` |
| `float` | `FLOAT` |
| `bool` | `BOOLEAN` |
| `dict` | `OBJECT` |
| `list` | `ARRAY` |

## Important

- ✅ **Détection automatique** : Le script analyse tes fonctions et suggère les bonnes configurations
- ✅ **Packages auto** : Détecte si numpy, pandas ou sentence-transformers sont nécessaires
- ✅ **Schéma flexible** : Lance les UDF avec ou sans schéma (MY_UDF ou SCHEMA.MY_UDF)
- ⚠️ **Une UDF = Une fonction** : Chaque UDF Snowflake utilise une seule fonction Python (le handler)

## Tips

- Utilise le mode intelligent (numéro) pour gagner du temps
- Les arguments sont convertis automatiquement (int, float, string, bool, null)
- Pour numpy/pandas, pense à ajouter les packages lors de la création
- N'oublie pas d'inclure le schéma si nécessaire (SCHEMA.UDF_NAME)
- N'oublie pas d'ajouter les packages nécessaires (numpy, pandas, etc.)
