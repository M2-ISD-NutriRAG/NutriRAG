import os
import sys
from typing import List, Dict, Optional, Tuple
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from shared.snowflake.client import SnowflakeClient
from app.utils.recipe_metadata_utils import build_recipe_context_prompt


class ConversationManager:
    """Manages conversation history and context for agent interactions."""

    def __init__(self, snowflake_client: SnowflakeClient):
        self.client = snowflake_client

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

        # Get recipe IDs from recent messages with metadata
        recipe_context = self._get_recipe_context_from_metadata(conversation_id)
        if recipe_context:
            context_parts.append(recipe_context)

        # Get recent search results from HIST_SEARCH for additional context
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

        except Exception:
            pass

        return []

    def _get_recipe_context_from_metadata(self, conversation_id: str) -> str:
        """
        Get recipe context from message metadata (recently shown recipes).
        This allows the agent to reference recipes by position without re-searching.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Formatted context string with recipe IDs, or empty string
        """
        try:
            # Get the most recent assistant message with search metadata
            result = self.client.execute(
                """
                SELECT metadata
                FROM MESSAGES
                WHERE conversation_id = %s
                  AND role = 'assistant'
                  AND metadata IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id,),
                fetch="one",
            )

            if result and result[0]:
                metadata = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                
                # Check if this has recipe_ids directly stored
                if metadata.get("type") == "search_results" and metadata.get("recipe_ids"):
                    # Recipe IDs are already in metadata - optimal case!
                    return build_recipe_context_prompt(
                        metadata["recipe_ids"],
                        metadata.get("query")
                    )
                
                # Fallback: if only search_executed, get IDs from HIST_SEARCH
                elif metadata.get("type") == "search_executed":
                    recipe_ids = self._get_recent_recipe_ids_from_hist_search(
                        conversation_id,
                        metadata.get("query")
                    )
                    
                    if recipe_ids:
                        return build_recipe_context_prompt(
                            recipe_ids,
                            metadata.get("query")
                        )

        except Exception:
            pass

        return ""

    def get_recent_recipe_ids(self, conversation_id: str) -> List[int]:
        """Return the list of recipe IDs from the most recent search in this conversation.

        Prefer IDs stored directly in MESSAGES.metadata (type = 'search_results').
        Fallback to HIST_SEARCH if only a query is stored (type = 'search_executed').
        """
        try:
            result = self.client.execute(
                """
                SELECT metadata
                FROM MESSAGES
                WHERE conversation_id = %s
                  AND role = 'assistant'
                  AND metadata IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(conversation_id,),
                fetch="one",
            )

            if result and result[0]:
                metadata = json.loads(result[0]) if isinstance(result[0], str) else result[0]

                if metadata.get("type") == "search_results" and metadata.get("recipe_ids"):
                    return [int(rid) for rid in metadata["recipe_ids"]]

                if metadata.get("type") == "search_executed":
                    return self._get_recent_recipe_ids_from_hist_search(
                        conversation_id,
                        metadata.get("query"),
                    )

        except Exception:
            pass

        return []

    def _get_recent_recipe_ids_from_hist_search(
        self,
        conversation_id: str,
        query: Optional[str] = None
    ) -> List[int]:
        """
        Get recipe IDs from HIST_SEARCH table for the most recent search.
        
        Args:
            conversation_id: The conversation ID
            query: Optional query filter to match specific search
            
        Returns:
            List of recipe IDs in order
        """
        try:
            if query:
                # Get recipes for a specific query
                result = self.client.execute(
                    """
                    SELECT RECIPE_ID
                    FROM ANALYTICS.HIST_SEARCH
                    WHERE conversation_id = %s
                      AND QUERY = %s
                    ORDER BY SEARCH_TIMESTAMP DESC, RECIPE_ID
                    LIMIT 10
                    """,
                    params=(conversation_id, query),
                    fetch="all",
                )
            else:
                # Get recipes from the most recent search
                result = self.client.execute(
                    """
                    SELECT RECIPE_ID
                    FROM ANALYTICS.HIST_SEARCH
                    WHERE conversation_id = %s
                    ORDER BY SEARCH_TIMESTAMP DESC, RECIPE_ID
                    LIMIT 10
                    """,
                    params=(conversation_id,),
                    fetch="all",
                )

            if result:
                return [int(row[0]) for row in result if row[0]]

        except Exception:
            pass

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
            # Get the latest assistant message with thread info
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
                return (
                    result[0],
                    result[1],
                )  # thread_id, message_id (to use as parent_message_id)

        except Exception:
            pass

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
            # Update the most recent message of this role with thread metadata
            self.client.execute(
                """
                UPDATE MESSAGES
                SET thread_id = %s, message_id = %s
                WHERE conversation_id = %s
                  AND role = %s
                  AND thread_id IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                params=(thread_id, message_id, conversation_id, role),
            )
        except Exception:
            pass

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

        except Exception:
            # Swallow errors to avoid breaking context generation
            pass

        return ""
