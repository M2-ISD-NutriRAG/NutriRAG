import json
from typing import List, Any, Dict
from snowflake.snowpark import Session


def parse_procedure_result(query_result, proc_name) -> Any:
    """
    Parse a procedure result parsed with query result to be usable.
    Args:
        query_result: query result parsed
        proc_name: procedure name

    Returns:
        output: Any
    """
    value = query_result[0][proc_name]
    output = json.loads(value)
    return output


def parse_query_result(query_result) -> List[Dict[str, float]]:
    """
    Collect query result and return as dict list
    Args:
        query_result : result of a query call (session.sql(query))

    Returns:
        List[Dict[str, float]]: formatted output
    """
    collected_result = query_result.collect()
    return [row.as_dict() for row in collected_result]


def format_output(input: Any) -> str:
    """
    Dumps output in json format to be usable.
    Args:
        input: Any type of data
    Returns:
        str: json result of the formatted output
    """
    # Convertir les Decimal en float pour la sérialisation JSON
    if (
        isinstance(input, list)
        and len(input) > 0
        and isinstance(input[0], dict)
    ):
        from decimal import Decimal

        for item in input:
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)

    # Retourner en JSON
    return json.dumps(input, indent=2)


def procedure_template(session: Session, arg1: Dict, arg2: List[str]) -> str:
    """
    Template procedure

    Args:
    session: Snowpark session implicitly init by snowflake
    arg1: dict type argument
    arg2: list type argument

    Returns:
    output: JSON string containing output.
    """
    # Query to fetch ingredient details
    query = """
    SELECT
        ci."DESCRIP",
        ci."PROTEIN_G",
        ci."SATURATED_FATS_G",
        ci."FAT_G",
        ci."CARB_G",
        ci."SODIUM_MG",
        ci."FIBER_G",
        ci."SUGAR_G",
        ci."ENERGY_KCAL",
        ci."NDB_NO",
    FROM NUTRIRAG_PROJECT.RAW.CLEANED_INGREDIENTS ci
    LIMIT 5;
    """

    result_query = session.sql(query)  # Run sql query
    data_list = parse_query_result(result_query)  # Parsed query result

    output = format_output(data_list)  # Dumps data in json format
    return output
