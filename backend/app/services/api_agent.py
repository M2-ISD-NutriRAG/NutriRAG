import os
import sys
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from shared.snowflake.client import SnowflakeClient


class CortexAgentClient:
    def __init__(self, snowflake_client: SnowflakeClient):
        self.sf = snowflake_client

    # create thread important to work on the same conversation
    def create_thread(self, origin_application: str = "NutriRAG"):
        token = self.sf.get_jwt()
        account = self.sf.config["account"]

        url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/threads"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
        }

        body = {"origin_application": origin_application}

        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=10
            )
            response.raise_for_status()
            
            # Parse response - could be a string or dict
            response_data = response.json()
            
            # Handle different response formats
            if isinstance(response_data, dict):
                # If dict, look for thread_id field
                thread_id = response_data.get('thread_id') or response_data.get('id')
                if thread_id is None:
                    print(f"Unexpected response format: {response_data}")
                    return None
                thread_id = int(thread_id)
            elif isinstance(response_data, (str, int)):
                # If string or int, use directly
                thread_id = int(response_data)
            else:
                print(f"Unexpected response type: {type(response_data)} - {response_data}")
                return None
            
            print(f"Successfully created thread: {thread_id}")
            return thread_id
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error creating thread: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Error creating thread: {type(e).__name__}: {str(e)}")
            return None

    def call_agent(
        self,
        prompt: str,
        thread_id: int = None,
        parent_message_id: int = None,
    ):

        # Call the Cortex Agent with a message, optionally continuing a thread.
        # prompt: The user's message (may include context)
        # thread_id: Thread ID for conversation continuity (optional)
        # parent_message_id: Parent message ID (last assistant message ID) for continuing conversation (optional)
        #                    Must be 0 for first message in a thread, otherwise the last assistant message_id

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
            "include_thinking": True,
            "tool_choice": {"type": "auto"},
        }

        # Add thread information if provided
        if thread_id is not None:
            body["thread_id"] = thread_id
            # parent_message_id must be 0 for first message, or the last assistant message_id
            body["parent_message_id"] = (
                parent_message_id if parent_message_id is not None else 0
            )

        return requests.post(
            url,
            headers=headers,
            json=body,
            stream=True,
            timeout=(10, 300),  # 10s connection, 300s read timeout
        )


# Example usage:
if __name__ == "__main__":
    sf_client = SnowflakeClient()
    agent_client = CortexAgentClient(snowflake_client=sf_client)
    r = agent_client.call_agent("Find me a recipe with chicken")

    print("Status:", r.status_code)
    print("---- STREAM START ----")
    for line in r.iter_lines(decode_unicode=True):
        # if line.startswith("data: "):
        # print(line[6:])
        print(line)
