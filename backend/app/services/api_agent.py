import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.snowflake.client import SnowflakeClient


class CortexAgentClient:
    def __init__(self, snowflake_client: SnowflakeClient):
        self.sf = snowflake_client

    def call_agent(self, prompt: str):
        token = self.sf.get_jwt()
        account = self.sf.config["account"]
        db = self.sf.config["database"]
        schema = self.sf.config["schema_agent"]
        agent = self.sf.config["agent"]

        url = f"https://{account}.snowflakecomputing.com/api/v2/databases/{db}/schemas/{schema}/agents/{agent}:run"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        }

        body = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
            "include_thinking": False,
            "tool_choice": {"type": "auto"},
        }

        return requests.post(url, headers=headers, json=body, stream=True)


# Example usage:
if __name__ == "__main__":
    sf_client = SnowflakeClient()
    agent_client = CortexAgentClient(snowflake_client=sf_client)
    r = agent_client.call_agent("Find me a recipe with chicken")

    print("Status:", r.status_code)
    print("---- STREAM START ----")
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            print(line[6:])
