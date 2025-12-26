import os
import sys
import re
import inspect
from typing import Optional, Dict, List, Tuple
from shared.snowflake.client import SnowflakeClient


def parse_function_signatures(file_path: str) -> Dict[str, Dict]:
    """Parse les signatures des fonctions dans le fichier UDF"""
    functions = {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Pattern pour capturer les fonctions avec leurs signatures et docstrings
    pattern = r'def\s+(\w+)\s*\((.*?)\)\s*->\s*(\w+):\s*"""(.*?)"""'
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        func_name = match.group(1)
        params_str = match.group(2).strip()
        return_type = match.group(3).strip()
        docstring = match.group(4).strip()
        
        # Parser les paramètres
        params = []
        if params_str:
            for param in params_str.split(','):
                param = param.strip()
                if ':' in param:
                    name, type_hint = param.split(':', 1)
                    name = name.strip()
                    type_hint = type_hint.strip()
                    params.append((name, type_hint))
        
        # Extraire les packages requis du docstring
        packages = []
        if 'numpy' in docstring.lower() or 'numpy' in params_str.lower():
            packages.append('numpy')
        if 'pandas' in docstring.lower() or 'pandas' in params_str.lower():
            packages.append('pandas')
        if 'sentence' in docstring.lower() or 'transformers' in docstring.lower():
            packages.append('sentence-transformers')
        
        # Extraire la description courte
        desc_lines = docstring.split('\n')
        short_desc = desc_lines[0] if desc_lines else ""
        
        functions[func_name] = {
            'params': params,
            'return_type': return_type,
            'description': short_desc,
            'packages': packages
        }
    
    return functions


def create_udf(
    session,
    code: str,
    udf_name: str,
    return_type: str,
    parameters: str,
    runtime_version: str = "3.10",
    packages: Optional[tuple] = None,
    imports: Optional[list] = None,
    external_access_integrations: Optional[str] = None,
    handler: str = "udf_handler"
):
    """
    Crée une UDF (User Defined Function) sur Snowflake
    
    Args:
        session: Session Snowpark
        code: Code Python de la UDF
        udf_name: Nom de la UDF
        return_type: Type de retour (ex: STRING, FLOAT, ARRAY, etc.)
        parameters: Paramètres de la UDF (ex: "INPUT_TEXT STRING, MAX_LENGTH INT")
        runtime_version: Version Python (défaut: 3.10)
        packages: Tuple des packages nécessaires
        imports: Liste des imports de fichiers stage
        external_access_integrations: Intégration d'accès externe si nécessaire
        handler: Nom de la fonction handler dans le code
    """
    
    # Construction de la clause PACKAGES
    packages_clause = ""
    if packages:
        packages_str = ", ".join([f"'{pkg}'" for pkg in packages])
        packages_clause = f"PACKAGES = ({packages_str})"
    
    # Construction de la clause IMPORTS
    imports_clause = ""
    if imports:
        imports_str = ", ".join([f"'{imp}'" for imp in imports])
        imports_clause = f"IMPORTS = ({imports_str})"
    
    # Construction de la clause EXTERNAL_ACCESS_INTEGRATIONS
    external_access_clause = ""
    if external_access_integrations:
        external_access_clause = f"EXTERNAL_ACCESS_INTEGRATIONS = ({external_access_integrations})"
    
    query = f"""
        CREATE OR REPLACE FUNCTION {udf_name}({parameters})
        RETURNS {return_type}
        LANGUAGE PYTHON
        RUNTIME_VERSION = '{runtime_version}'
        {packages_clause}
        {imports_clause}
        {external_access_clause}
        HANDLER = '{handler}'
        AS
        $$
{code}
        $$
    """

    print(f"\n{'='*60}")
    print(f"Déploiement de la UDF : {udf_name}")
    print(f"{'='*60}")
    print(f"Paramètres : {parameters}")
    print(f"Type de retour : {return_type}")
    print(f"Handler : {handler}")
    if packages:
        print(f"Packages : {', '.join(packages)}")
    print(f"{'='*60}\n")
    
    try:
        result = session.sql(query).collect()
        print(f"✓ Succès : UDF '{udf_name}' créée avec succès!")
        return True
    except Exception as e:
        print(f"✗ Erreur lors du déploiement : {e}")
        raise e


def read_udf_code(file_path: str) -> str:
    """Lit le code Python qui contient la logique de la UDF"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Le fichier {file_path} n'existe pas")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def map_python_to_snowflake_type(python_type: str) -> str:
    """Convertit un type Python en type Snowflake"""
    type_map = {
        'str': 'STRING',
        'int': 'INT',
        'float': 'FLOAT',
        'bool': 'BOOLEAN',
        'dict': 'OBJECT',
        'list': 'ARRAY',
        'Any': 'VARIANT'
    }
    return type_map.get(python_type, 'STRING')


def interactive_mode():
    """Mode interactif pour créer une UDF"""
    print("\n" + "="*60)
    print("CRÉATION INTERACTIVE D'UNE UDF SNOWFLAKE")
    print("="*60 + "\n")
    
    # 1. Fichier source
    default_file = os.path.join(os.path.dirname(__file__), "snowflake_udf.py")
    file_path = input(f"Chemin du fichier Python source [{default_file}]: ").strip()
    if not file_path:
        file_path = default_file
    
    if not os.path.exists(file_path):
        print(f"✗ Le fichier {file_path} n'existe pas!")
        sys.exit(1)
    
    # 2. Parser les fonctions disponibles
    print(f"\nAnalyse du fichier {file_path}...")
    functions = parse_function_signatures(file_path)
    
    if not functions:
        print("Aucune fonction trouvée dans le fichier!")
        print("Mode manuel activé.\n")
    else:
        print("\n✓ Fonctions disponibles:")
        print("-" * 60)
        for i, (func_name, info) in enumerate(functions.items(), 1):
            params_str = ', '.join([f"{name}: {type_}" for name, type_ in info['params']])
            print(f"{i}. {func_name}({params_str}) -> {info['return_type']}")
            print(f"   {info['description']}")
            if info['packages']:
                print(f"Packages: {', '.join(info['packages'])}")
            print()
    
    # 3. Choix de la fonction
    selected_func = None
    handler = "udf_handler"
    parameters = ""
    return_type = "STRING"
    packages = ["snowflake-snowpark-python"]
    
    if functions:
        choice = input("Choisir une fonction (numéro) ou M pour mode manuel [M]: ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(functions):
            # Fonction sélectionnée
            func_name = list(functions.keys())[int(choice) - 1]
            selected_func = functions[func_name]
            handler = func_name
            
            # Générer les paramètres Snowflake
            params_list = []
            for param_name, param_type in selected_func['params']:
                snowflake_type = map_python_to_snowflake_type(param_type)
                params_list.append(f"{param_name.upper()} {snowflake_type}")
            parameters = ", ".join(params_list)
            
            return_type = map_python_to_snowflake_type(selected_func['return_type'])
            
            # Packages recommandés
            if selected_func['packages']:
                packages.extend(selected_func['packages'])
            
            print(f"\n✓ Fonction sélectionnée: {handler}")
            print(f"  Paramètres: {parameters}")
            print(f"  Retour: {return_type}")
            print(f"  Packages: {', '.join(packages)}")
            
            # Demander si l'utilisateur veut modifier
            modify = input("\nModifier ces valeurs? (o/N): ").strip().lower()
            if modify == 'o':
                selected_func = None  # Passer en mode manuel
    
    # 4. Mode manuel ou modification
    if selected_func is None:
        print("\nMode manuel")
        handler = input(f"Fonction handler [{handler}]: ").strip() or handler
        
        print("\nExemple: INPUT_TEXT STRING, MAX_LENGTH INT")
        custom_params = input(f"Paramètres [{parameters}]: ").strip()
        if custom_params:
            parameters = custom_params
        
        if not parameters:
            print("✗ Les paramètres sont requis!")
            sys.exit(1)
        
        print("\nTypes: STRING, INT, FLOAT, BOOLEAN, ARRAY, OBJECT, VARIANT")
        custom_return = input(f"Type de retour [{return_type}]: ").strip()
        if custom_return:
            return_type = custom_return
        
        print(f"\nPackages actuels: {', '.join(packages)}")
        additional = input("Ajouter packages (séparés par virgules): ").strip()
        if additional:
            packages.extend([p.strip() for p in additional.split(',')])
    
    # 5. Nom de la UDF dans Snowflake
    suggested_name = handler.upper().replace("_", "_")
    udf_name = input(f"\nNom UDF Snowflake [{suggested_name}]: ").strip() or suggested_name
    
    # 6. Options avancées
    runtime = input("Version Python [3.10]: ").strip() or "3.10"
    external_access = input("Intégration accès externe (optionnel): ").strip() or None
    
    # Confirmation
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    print(f"Fichier   : {os.path.basename(file_path)}")
    print(f"Handler   : {handler}")
    print(f"Nom UDF   : {udf_name}")
    print(f"Paramètres: {parameters}")
    print(f"Retour    : {return_type}")
    print(f"Runtime   : Python {runtime}")
    print(f"Packages  : {', '.join(packages)}")
    if external_access:
        print(f"Accès ext : {external_access}")
    print("="*60 + "\n")
    
    confirm = input("Créer la UDF? (o/N): ").strip().lower()
    if confirm != 'o':
        print("✗ Annulé.")
        sys.exit(0)
    
    # Lecture du code
    print(f"\nLecture du code...")
    code = read_udf_code(file_path)
    
    # Connexion à Snowflake
    print("Connexion à Snowflake...")
    client = SnowflakeClient()
    session = client.get_snowpark_session()
    
    try:
        # Création de la UDF
        create_udf(
            session=session,
            code=code,
            udf_name=udf_name,
            return_type=return_type,
            parameters=parameters,
            runtime_version=runtime,
            packages=tuple(packages),
            external_access_integrations=external_access,
            handler=handler
        )
        
        print("\n" + "="*60)
        print("✓ UDF CRÉÉE!")
        print("="*60)
        print(f"\nUtilisation:")
        print(f"  SELECT {udf_name}(...)")
        print(f"\nTest:")
        print(f"  python -m data.launch_udf")
        
    finally:
        session.close()


def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1:
        # Mode non-interactif (pour usage programmatique)
        print("Usage: python create_udf.py")
        print("Lance le script sans arguments pour le mode interactif.")
        sys.exit(1)
    
    try:
        interactive_mode()
    except KeyboardInterrupt:
        print("\n\n✗ Création interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
