import sys
from typing import Any, List
from snowflake.snowpark import Session
from shared.snowflake.client import SnowflakeClient


def execute_udf(session: Session, udf_name: str, arguments: List[Any], format_output: bool = True):
    """
    Exécute une UDF sur Snowflake avec les arguments fournis
    
    Args:
        session: Session Snowpark
        udf_name: Nom de la UDF à exécuter
        arguments: Liste des arguments à passer à la UDF
        format_output: Si True, affiche le résultat de manière formatée
    
    Returns:
        Le résultat de l'exécution de la UDF
    """
    
    # Formater les arguments pour SQL
    formatted_args = []
    for arg in arguments:
        if isinstance(arg, str):
            # Échapper les guillemets simples et entourer de guillemets
            escaped_arg = arg.replace("'", "''")
            formatted_args.append(f"'{escaped_arg}'")
        elif isinstance(arg, bool):
            formatted_args.append(str(arg).upper())
        elif arg is None:
            formatted_args.append("NULL")
        elif isinstance(arg, (list, dict)):
            # Pour les types complexes, utiliser PARSE_JSON
            import json
            json_str = json.dumps(arg).replace("'", "''")
            formatted_args.append(f"PARSE_JSON('{json_str}')")
        else:
            formatted_args.append(str(arg))
    
    args_str = ", ".join(formatted_args)
    query = f"SELECT {udf_name}({args_str})"
    
    print(f"\n{'='*60}")
    print(f"EXÉCUTION DE LA UDF : {udf_name}")
    print(f"{'='*60}")
    print(f"Requête SQL: {query}")
    print(f"{'='*60}\n")
    
    try:
        print("Exécution en cours...")
        result = session.sql(query).collect()
        
        if format_output:
            print(f"\n{'='*60}")
            print("RÉSULTAT")
            print(f"{'='*60}")
            if result:
                output = result[0][0]
                print(f"{output}")
            else:
                print("Aucun résultat retourné")
            print(f"{'='*60}\n")
        
        return result[0][0] if result else None
        
    except Exception as e:
        print(f"✗ Erreur lors de l'exécution : {e}")
        raise e


def test_udf_on_table(session: Session, udf_name: str, table_name: str, column_name: str, limit: int = 5):
    """
    Teste une UDF sur une colonne d'une table
    
    Args:
        session: Session Snowpark
        udf_name: Nom de la UDF
        table_name: Nom de la table
        column_name: Nom de la colonne à passer à la UDF
        limit: Nombre de lignes à traiter
    """
    
    query = f"""
    SELECT 
        {column_name} AS INPUT_VALUE,
        {udf_name}({column_name}) AS OUTPUT_VALUE
    FROM {table_name}
    LIMIT {limit}
    """
    
    print(f"\n{'='*60}")
    print(f"TEST DE LA UDF SUR TABLE")
    print(f"{'='*60}")
    print(f"Table: {table_name}")
    print(f"Colonne: {column_name}")
    print(f"Limite: {limit} lignes")
    print(f"{'='*60}\n")
    
    try:
        print("Exécution en cours...")
        result = session.sql(query).collect()
        
        print(f"\n{'='*60}")
        print("RÉSULTATS")
        print(f"{'='*60}")
        for i, row in enumerate(result, 1):
            print(f"\nLigne {i}:")
            print(f"  Input : {row['INPUT_VALUE']}")
            print(f"  Output: {row['OUTPUT_VALUE']}")
        print(f"\n{'='*60}\n")
        
        return result
        
    except Exception as e:
        print(f"✗ Erreur lors du test : {e}")
        raise e


def interactive_mode():
    """Mode interactif pour exécuter une UDF"""
    print("\n" + "="*60)
    print("LANCER UNE UDF SNOWFLAKE")
    print("="*60 + "\n")
    
    # Connexion à Snowflake
    print("🔌 Connexion à Snowflake...")
    client = SnowflakeClient()
    session = client.get_snowpark_session()
    
    try:
        # 1. Nom de la UDF (avec schéma si nécessaire)
        print("Nom de la UDF (ex: MY_UDF ou SCHEMA.MY_UDF)")
        udf_name = input("UDF: ").strip()
        if not udf_name:
            print("✗ Le nom de la UDF est requis!")
            sys.exit(1)
        
        # 2. Arguments
        print("\nEntrez les arguments (un par ligne, ligne vide pour terminer):")
        arguments = []
        i = 1
        while True:
            arg = input(f"Argument {i}: ").strip()
            if not arg:
                break
            
            # Conversion de type automatique
            try:
                arguments.append(int(arg))
            except ValueError:
                try:
                    arguments.append(float(arg))
                except ValueError:
                    if arg.lower() == "true":
                        arguments.append(True)
                    elif arg.lower() == "false":
                        arguments.append(False)
                    elif arg.lower() == "null":
                        arguments.append(None)
                    else:
                        arguments.append(arg)
            i += 1
        
        if not arguments:
            print("✗ Au moins un argument requis!")
            sys.exit(1)
        
        # 3. Exécution
        execute_udf(session, udf_name, arguments)
        print("\n✓ Terminé!")
        
    except KeyboardInterrupt:
        print("\n\n✗ Interrompu.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        sys.exit(1)
    finally:
        session.close()


def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1:
        print("Usage: python launch_udf.py")
        print("Lance le script sans arguments pour le mode interactif.")
        sys.exit(1)
    
    try:
        interactive_mode()
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
