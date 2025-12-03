import os
import json
import jwt
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv


class CortexAgentClient:
    def __init__(self, env_path: str = ".env"):
        # Load environment file
        load_dotenv(env_path)
        # --- Snowflake config ---
        self.account = os.getenv("SNOWFLAKE_ACCOUNT").upper()
        self.user = os.getenv("SNOWFLAKE_USER").upper()
        self.database = os.getenv("SNOWFLAKE_DATABASE")
        self.schema = os.getenv("SNOWFLAKE_SERVICES_SCHEMA")
        self.agent = os.getenv("AGENT_NAME")
        self.public_key_fp = os.getenv("PUBLIC_KEY_FP")

        # Paths
        self.private_key_path = Path(os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"))
        self.token_cache_path = Path(os.getenv("PRIVATE_KEY_PATH"))

        # Load private RSA key
        self.private_key = self.private_key_path.read_text()

        # Load or generate token
        self.token = self._load_or_generate_token()

    # -------------------------------------------------------
    # TOKEN MANAGEMENT
    # -------------------------------------------------------
    def _load_token_from_cache(self):
        """Return the cached token if exists and not expired."""
        if not self.token_cache_path.exists():
            return None

        try:
            data = json.loads(self.token_cache_path.read_text())
            exp = datetime.fromisoformat(data["exp"])

            if exp > datetime.now(timezone.utc):
                print("[OK] Token loaded from cache (valid)")
                return data["token"]

            print("[INFO] Cached token expired")
            return None

        except Exception:
            return None

    def _save_token_to_cache(self, token, exp):
        """Save JWT and expiration date."""
        data = {"token": token, "exp": exp.isoformat()}
        self.token_cache_path.write_text(json.dumps(data))

    def _generate_jwt(self):
        """Generate a long-lived JWT (allowed for Cortex Agents)."""
        now = datetime.now(timezone.utc)
        exp = now.replace(year=now.year + 10) 

        payload = {
            "iss": f"{self.account}.{self.user}.{self.public_key_fp}",
            "sub": f"{self.account}.{self.user}",
            "iat": now,
            "exp": exp,
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        self._save_token_to_cache(token, exp)

        print("[OK] New token generated and cached")
        return token

    def _load_or_generate_token(self):
        """Return a valid token, generating one if needed."""
        token = self._load_token_from_cache()
        if token is not None:
            return token
        return self._generate_jwt()


    def call_agent(self, user_message: str):
        """Call Cortex agent and stream the response."""

        url = (
            f"https://{self.account}.snowflakecomputing.com/"
            f"api/v2/databases/{self.database}/schemas/{self.schema}/agents/{self.agent}:run"
        )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        }

        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
            "tool_choice": {"type": "auto"},
            "include_thinking": False,
        }

        print("[INFO] Calling agent:", self.agent)

        with requests.post(url, headers=headers, json=body, stream=True) as r:
            print("Status:", r.status_code)
            print("---- STREAM START ----")

            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    print(line[6:])

            print("---- STREAM END ----")

# Example usage:
if __name__ == "__main__":
    client = CortexAgentClient()
    client.call_agent("Find me a recipe with chicken")
