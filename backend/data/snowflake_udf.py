"""
Exemples de UDF Snowflake simples pour tests.
Ce fichier sera lu par create_udf.py pour créer la UDF.

Modifiez ce fichier selon vos besoins, puis exécutez:
  python create_udf.py
"""


def udf_handler(name: str) -> str:
    """
    Simple Hello World UDF.
    
    Args:
        name: Nom de la personne
    
    Returns:
        Message de bienvenue
    """
    return f"Hello World, {name}!"


def udf_square(x: float) -> float:
    """
    Calcule le carré d'un nombre.
    
    Args:
        x: Nombre à élever au carré
    
    Returns:
        x²
    """
    return x ** 2


def udf_add(a: float, b: float) -> float:
    """
    Additionne deux nombres.
    
    Args:
        a: Premier nombre
        b: Deuxième nombre
    
    Returns:
        a + b
    """
    return a + b


def udf_numpy_mean(numbers_json: str) -> float:
    """
    Calcule la moyenne d'une liste de nombres avec numpy.
    
    Args:
        numbers_json: Liste de nombres au format JSON (ex: "[1, 2, 3, 4, 5]")
    
    Returns:
        Moyenne des nombres
    
    Note: Ajouter 'numpy' dans les packages lors de la création
    """
    import numpy as np
    import json
    
    numbers = json.loads(numbers_json)
    return float(np.mean(numbers))


def udf_numpy_std(numbers_json: str) -> float:
    """
    Calcule l'écart-type d'une liste de nombres avec numpy.
    
    Args:
        numbers_json: Liste de nombres au format JSON
    
    Returns:
        Écart-type des nombres
    
    Note: Ajouter 'numpy' dans les packages lors de la création
    """
    import numpy as np
    import json
    
    numbers = json.loads(numbers_json)
    return float(np.std(numbers))


def udf_numpy_operations(a: float, b: float) -> str:
    """
    Effectue plusieurs opérations mathématiques avec numpy.
    
    Args:
        a: Premier nombre
        b: Deuxième nombre
    
    Returns:
        JSON avec les résultats des opérations
    
    Note: Ajouter 'numpy' dans les packages lors de la création
    """
    import numpy as np
    import json
    
    results = {
        "sum": float(np.add(a, b)),
        "difference": float(np.subtract(a, b)),
        "product": float(np.multiply(a, b)),
        "quotient": float(np.divide(a, b)) if b != 0 else None,
        "power": float(np.power(a, b)),
        "sqrt_a": float(np.sqrt(a)) if a >= 0 else None,
        "sqrt_b": float(np.sqrt(b)) if b >= 0 else None,
    }
    
    return json.dumps(results)
