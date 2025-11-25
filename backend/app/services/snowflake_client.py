import os
from typing import Optional
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session


class SnowflakeClient:
    # Singleton Snowflake client
    _instance: Optional[Session] = None

    @classmethod
    def get_session(cls) -> Session:
        # Obtenir ou créer une session Snowflake
        # Dans l'environnement de production/Snowflake: uses get_active_session()
        # Dans l'environnement de développement: creates session from credentials

        if cls._instance is not None:
            return cls._instance

        try:
            # Try to get active session (works in Snowflake environment)
            cls._instance = get_active_session()
            print("Utilisation de la session Snowflake active")
        except Exception:
            # Create new session from credentials
            connection_params = {
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PASSWORD"),
                "role": os.getenv("SNOWFLAKE_ROLE"),
                "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
                "database": os.getenv("SNOWFLAKE_DATABASE"),
                "schema": os.getenv("SNOWFLAKE_SCHEMA"),
            }

            # Validate required params
            if not all(
                [
                    connection_params["account"],
                    connection_params["user"],
                    connection_params["password"],
                ]
            ):
                raise ValueError(
                    "Missing Snowflake credentials. Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD"
                )

            cls._instance = Session.builder.configs(connection_params).create()
            print("Création d'une nouvelle session Snowflake")

        return cls._instance

    @classmethod
    def close(cls):
        # Fermer la session Snowflake
        if cls._instance:
            cls._instance.close()
            cls._instance = None


def get_snowflake_session() -> Session:
    # Fonction de conveniance pour obtenir la session Snowflake
    return SnowflakeClient.get_session()
