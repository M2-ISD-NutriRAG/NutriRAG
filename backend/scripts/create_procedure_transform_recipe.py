import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.snowflake.client import SnowflakeClient


def read_code(file_path):
    """Lit le code Python qui contient la logique (sp_handler, imports, etc.)"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    sf_client = SnowflakeClient()
    session = sf_client.get_snowpark_session()

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        script_dir, "..", "app", "services", "transform_recipe.py"
    )
    code = read_code(file_path)

    # 3. Déploiement de la Procédure Stockée
    schema = "NUTRIRAG_PROJECT.SERVICES"
    proc_name = "TRANSFORM_RECIPE"
    full_proc_name = f"{schema}.{proc_name}"
    main_func_name = "transform_recipe"
    args = ["REQUEST"]
    query = f"""
        CREATE OR REPLACE PROCEDURE {full_proc_name}({" STRING, ".join(args) + " STRING"})
        RETURNS STRING
        LANGUAGE PYTHON
        RUNTIME_VERSION = '3.10'
        PACKAGES = ('snowflake-snowpark-python', 'filelock', 'pydantic')
        EXTERNAL_ACCESS_INTEGRATIONS = (TRAINING_INTERNET_ACCESS)
        HANDLER = '{main_func_name}'
        EXECUTE AS OWNER
        AS
        $${code}$$
    """

    print(session.sql(query).collect())

    sf_client.close()


if __name__ == "__main__":
    main()
