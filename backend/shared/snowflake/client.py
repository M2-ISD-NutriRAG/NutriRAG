"""Snowflake client with key pair authentication support."""

import os
from dotenv import load_dotenv
from typing import Any, Literal, Optional
from snowflake.snowpark import Session
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import jwt


def _load_private_key(private_key_path: str) -> bytes:
    """Load private key for Snowflake key pair authentication.

    Args:
        private_key_path: Path to the private key file (.p8 format)

    Returns:
        Private key bytes in DER format

    Raises:
        FileNotFoundError: If the private key file does not exist.
        ValueError: If the private key file contains invalid key data.
        PermissionError: If the private key file cannot be read due to permissions.
    """
    try:
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None
            )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Private key file not found at '{private_key_path}'. "
            "Please ensure the SNOWFLAKE_PRIVATE_KEY_PATH is correct."
        ) from e
    except PermissionError as e:
        raise PermissionError(
            f"Unable to read private key file at '{private_key_path}'. "
            "Please check file permissions."
        ) from e
    except Exception as e:
        raise ValueError(
            f"Invalid private key data in '{private_key_path}'. "
            "Please ensure the file contains a valid PEM-encoded private key."
        ) from e

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


class SnowflakeClient:
    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        account: Optional[str] = None,
        role: Optional[str] = None,
        warehouse: Optional[str] = None,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        private_key_path: Optional[str] = None,
        autoconnect: bool = True,
        schema_agent: Optional[str] = None,
        agent: Optional[str] = None,
        public_key_fp: Optional[str] = None,
        token_cache_path: Optional[str] = None,
    ) -> None:
        # Load .env file once
        load_dotenv()

        # Determine authentication method
        private_key_path = private_key_path or os.getenv(
            "SNOWFLAKE_PRIVATE_KEY_PATH"
        )
        use_key_pair = private_key_path is not None

        self.config = {
            "user": user or os.getenv("SNOWFLAKE_USER"),
            "account": account or os.getenv("SNOWFLAKE_ACCOUNT"),
            "role": role or os.getenv("SNOWFLAKE_ROLE"),
            "warehouse": warehouse or os.getenv("SNOWFLAKE_WAREHOUSE"),
            "database": database or os.getenv("SNOWFLAKE_DATABASE"),
            "schema": schema or os.getenv("SNOWFLAKE_SCHEMA"),
            "schema_agent": schema_agent
            or os.getenv("SNOWFLAKE_SERVICES_SCHEMA"),
            "agent": agent or os.getenv("AGENT_NAME"),
            "public_key_fp": public_key_fp or os.getenv("PUBLIC_KEY_FP"),
            "token_cache_path": token_cache_path
            or Path(os.getenv("PRIVATE_KEY_PATH")),
            "private_key_jwt": Path(
                os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
            ).read_text(),
        }

        # Add authentication - either key pair or password
        if use_key_pair:
            # Use key pair authentication (recommended for MFA accounts)
            self.config["private_key"] = _load_private_key(private_key_path)
        else:
            # Fall back to password authentication
            self.config["password"] = password or os.getenv(
                "SNOWFLAKE_PASSWORD"
            )
            if not self.config["password"]:
                raise ValueError(
                    "Either SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PASSWORD environment variable must be set"
                )

        # Add OCSP fail open for certificate issues
        self.config["ocsp_fail_open"] = True


        # Enable insecure mode inorder to upload local files to snowflake stage
        self.config["insecure_mode"] = True


        # Verify required fields
        required_fields = [
            "user",
            "account",
            "role",
            "warehouse",
            "database",
            "schema",
        ]
        missing = [k for k in required_fields if self.config.get(k) is None]
        if missing:
            raise ValueError(
                f"Missing Snowflake config values: {', '.join(missing)}"
            )

        self._conn = None
        self._snowpark_session = None

        if autoconnect:
            self.connect()

    def connect(self) -> None:
        """Open a connection if not already open."""
        if self._conn is not None and not self._conn.is_closed():
            return

        try:
            self._conn = snowflake.connector.connect(**self.config)
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Snowflake: {str(e)}"
            ) from e

    def close(self) -> None:
        """Close both connector and Snowpark sessions if open."""
        if self._conn is not None and not self._conn.is_closed():
            self._conn.close()
        self.close_snowpark_session()

    def get_snowpark_session(self) -> Session:
        """Get or create a Snowpark session using the same credentials.

        Returns:
            Session: Snowpark session for DataFrame operations.

        Note:
            The session is cached and reused. Call close_snowpark_session()
            to explicitly close it, or it will be closed when the client
            is used as a context manager.
        """
        # Check if session needs to be created or recreated
        session_invalid = False
        if self._snowpark_session is not None:
            try:
                # Try a trivial query to check if session is valid
                self._snowpark_session.sql("SELECT 1").collect()
            except Exception:
                session_invalid = True

        if self._snowpark_session is None or session_invalid:
            # Build session config - remove password before copying if using key pair
            session_config = self.config.copy()

            # Remove authenticator setting if it exists (let Snowflake auto-detect from private_key)
            session_config.pop("authenticator", None)

            # Add passcode if available (for MFA with password auth)
            passcode = os.getenv("SNOWFLAKE_PASSCODE")
            if passcode and "password" in session_config:
                session_config["passcode"] = passcode

            self._snowpark_session = Session.builder.configs(
                session_config
            ).create()

        return self._snowpark_session

    def close_snowpark_session(self) -> None:
        """Close the Snowpark session if open."""
        if self._snowpark_session is not None:
            try:
                self._snowpark_session.close()
            except Exception:
                pass  # Session might already be closed
            finally:
                self._snowpark_session = None

    def __enter__(self) -> "SnowflakeClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        """Redact sensitive fields when object is printed or logged."""
        safe_config = {
            k: "***REDACTED***" if k in ("password", "private_key") else v
            for k, v in self.config.items()
        }
        return f"SnowflakeClient(config={safe_config})"

    def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: Optional[Literal["one", "all"]] = None,
    ) -> Optional[Any]:
        """
        Execute a query.

        fetch can be:
        - None -> don't fetch, just execute (INSERT/UPDATE/etc)
        - "one" -> fetchone()
        - "all" -> fetchall()
        """
        if self._conn is None or self._conn.is_closed():
            self.connect()

        cur = self._conn.cursor()
        try:
            cur.execute(query, params or ())
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return None
        finally:
            cur.close()

    def is_connected(self) -> dict:
        """
        Run a basic health check against Snowflake.
        Returns info dict (version, ok flag).
        """
        ok = self._conn is not None and not self._conn.is_closed()
        version = None
        if ok:
            cur = None
            try:
                cur = self._conn.cursor()
                cur.execute("SELECT CURRENT_VERSION()")
                version = cur.fetchone()[0]
            except Exception:
                version = None
            finally:
                if cur is not None:
                    cur.close()
        return {"ok": ok, "version": version}

    # -------------------------------------------------------
    # JWT TOKEN MANAGEMENT FOR CORTEX
    # -------------------------------------------------------
    def _load_token_from_cache(self):
        cache_file = self.config["token_cache_path"]
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            exp = datetime.fromisoformat(data["exp"])

            if exp > datetime.now(timezone.utc):
                return data["token"]
            return None

        except Exception:
            return None

    def _save_token_to_cache(self, token, exp):
        cache_file = self.config["token_cache_path"]
        data = {"token": token, "exp": exp.isoformat()}
        cache_file.write_text(json.dumps(data))

    def _generate_jwt(self):
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=1)

        payload = {
            "iss": f"{self.config['account'].upper()}.{self.config['user'].upper()}.{self.config['public_key_fp']}",
            "sub": f"{self.config['account'].upper()}.{self.config['user'].upper()}",
            "iat": now,
            "exp": exp,
        }

        token = jwt.encode(
            payload, self.config["private_key_jwt"], algorithm="RS256"
        )
        self._save_token_to_cache(token, exp)
        return token

    def get_jwt(self) -> str:
        """Public method: returns a valid JWT for Cortex Agents."""
        token = self._load_token_from_cache()
        if token:
            return token
        return self._generate_jwt()
