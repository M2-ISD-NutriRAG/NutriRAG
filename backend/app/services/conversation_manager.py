import os
import sys
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from shared.snowflake.client import SnowflakeClient


class ConversationManager:
    # Manages conversation history and context for agent interactions

    def __init__(self, snowflake_client: SnowflakeClient):
        self.client = snowflake_client

    def create_or_get_thread(self, conversation_id: str, agent_client):
        # Create a new thread for a conversation if it doesn't exist, or get the existing thread_id.
        # Args:
        #     conversation_id: The conversation ID
        #     agent_client: CortexAgentClient instance for creating threads
        # Returns:
        #     Thread ID (integer) or None if thread creation fails (will use non-threaded mode)

        # Check if this conversation already has a thread
        thread_info = self.get_thread_info(conversation_id)
        if thread_info:
            print(f"Reusing existing thread: {thread_info[0]}")
            return thread_info[0]  # Return existing thread_id

        # Create a new thread
        thread_id = agent_client.create_thread(origin_application="NutriRAG")
        if thread_id is None:
            print(f"Warning: Failed to create thread for conversation {conversation_id}. Continuing without thread support.")
            return None

        # Store the thread_id in the most recent user message immediately
        # This ensures the next message in the conversation can find and reuse this thread
        try:
            result = self.client.execute(
                """
                SELECT id FROM MESSAGES
                WHERE conversation_id = %s
                  AND role = 'user'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id,),
                fetch="one"
            )
            
            if result:
                msg_id = result[0]
                self.client.execute(
                    """
                    UPDATE MESSAGES
                    SET thread_id = %s
                    WHERE id = %s
                    """,
                    params=(thread_id, msg_id),
                )
                # print(f"Stored thread_id {thread_id} for conversation {conversation_id}")
        except Exception as e:
            print(f"Warning: Could not store initial thread_id: {str(e)}")

        return thread_id

    def get_conversation_context(self, conversation_id: str) -> str:
        """
        Build a context string from recent conversation history and search results.
        This provides the agent with context about previous interactions.

        Args:
            conversation_id: The conversation ID

        Returns:
            Context string to prepend to the current message
        """
        context_parts = []

        # Get recent search results for context
        search_context = self._get_search_context(conversation_id)
        if search_context:
            context_parts.append(
                f"PREVIOUS SEARCH RESULTS IN THIS CONVERSATION:\n{search_context}"
            )

        # Get recent messages for additional context (more detailed than before)
        recent_messages = self._get_recent_messages(conversation_id)
        if recent_messages:
            messages_text = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in recent_messages]
            )
            context_parts.append(
                f"RECENT CONVERSATION HISTORY:\n{messages_text}"
            )

        if context_parts:
            return (
                "\n\n".join(context_parts)
                + "\n\n=== CURRENT USER MESSAGE ===\n"
            )

        return ""

    def _get_recent_messages(
        self, conversation_id: str, limit: int = 4
    ) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        try:
            # Get last few messages (excluding the current one we just inserted)
            result = self.client.execute(
                """
                SELECT role, content
                FROM MESSAGES
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET 1
                """,
                params=(conversation_id, limit),
                fetch="all",
            )

            if result:
                # Reverse to get chronological order
                messages = []
                for row in reversed(result):
                    messages.append({"role": row[0], "content": row[1]})
                return messages

        except Exception as e:
            print(f"Warning: Could not retrieve recent messages: {str(e)}")

        return []

    def get_thread_info(
        self, conversation_id: str
    ) -> Optional[Tuple[int, int]]:
        """
        Get the latest thread_id and message_id for a conversation to use as parent_message_id.

        Args:
            conversation_id: The conversation ID

        Returns:
            Tuple of (thread_id, parent_message_id) or None if no thread exists
        """
        try:
            # First, try to get the latest assistant message with both thread_id and message_id
            result = self.client.execute(
                """
                SELECT thread_id, message_id
                FROM MESSAGES
                WHERE conversation_id = %s
                  AND role = 'assistant'
                  AND thread_id IS NOT NULL
                  AND message_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id,),
                fetch="one",
            )

            if result:
                # print(f"Found thread info with message_id: thread_id={result[0]}, message_id={result[1]}")
                return (result[0], result[1])  # thread_id, message_id (to use as parent_message_id)
            
            # If no assistant message with message_id, check if we have any message with thread_id
            # This means we created the thread but haven't received any assistant responses yet
            result = self.client.execute(
                """
                SELECT thread_id
                FROM MESSAGES
                WHERE conversation_id = %s
                  AND thread_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id,),
                fetch="one",
            )
            
            if result:
                # print(f"Found thread_id without message_id: thread_id={result[0]}, will use parent_message_id=0")
                return (result[0], 0)  # thread_id exists, but use 0 as parent_message_id (first message)

        except Exception as e:
            print(f"Warning: Could not retrieve thread info: {str(e)}")

        return None

    def store_thread_metadata(
        self, conversation_id: str, role: str, thread_id: int, message_id: int
    ):
        """
        Store thread and message metadata from Cortex API response.

        Args:
            conversation_id: The conversation ID
            role: Message role ('user' or 'assistant')
            thread_id: Thread ID from Cortex API
            message_id: Message ID from Cortex API
        """
        try:
            # Find the most recent message ID for this role that doesn't have metadata yet
            result = self.client.execute(
                """
                SELECT id FROM MESSAGES
                WHERE conversation_id = %s
                  AND role = %s
                  AND thread_id IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id, role),
                fetch="one"
            )
            
            if result:
                msg_id = result[0]
                # Update with thread metadata
                self.client.execute(
                    """
                    UPDATE MESSAGES
                    SET thread_id = %s, message_id = %s
                    WHERE id = %s
                    """,
                    params=(thread_id, message_id, msg_id),
                )
                # print(f"Stored thread metadata: thread_id={thread_id}, message_id={message_id}, role={role}")
            else:
                print(f"Warning: No message found to update for role={role}, conversation_id={conversation_id}")
        except Exception as e:
            print(f"Warning: Could not store thread metadata: {str(e)}")

    def _get_search_context(self, conversation_id: str) -> str:
        """Get context from recent search results."""
        try:
            # Simpler query - let application handle numbering
            search_results = self.client.execute(
                """
                SELECT RECIPE_ID, NAME, QUERY
                FROM ANALYTICS.HIST_SEARCH
                WHERE conversation_id = %s
                ORDER BY QUERY, SEARCH_TIMESTAMP DESC
                """,
                params=(conversation_id,),
                fetch="all",
            )

            if search_results:
                context_parts = []
                current_query = None
                recipe_list = []
                recipe_count = 0

                for row in search_results:
                    recipe_id = row[0]
                    recipe_name = row[1]
                    query = row[2]

                    if recipe_id and recipe_name and query:
                        # Group recipes by query
                        if current_query != query:
                            if recipe_list:
                                context_parts.append(
                                    f"Search for '{current_query}': {', '.join(recipe_list)}"
                                )
                            current_query = query
                            recipe_list = []
                            recipe_count = 0

                        recipe_count += 1
                        # Limit to top 3 per query
                        if recipe_count <= 3:
                            recipe_list.append(
                                f"{recipe_count}. {recipe_name} (ID: {recipe_id})"
                            )

                # Add the last group
                if recipe_list and current_query:
                    context_parts.append(
                        f"Search for '{current_query}': {', '.join(recipe_list)}"
                    )

                return "; ".join(context_parts)

        except Exception as e:
            # Log the error but don't fail the request
            print(f"Warning: Could not retrieve search context: {str(e)}")

        return ""
