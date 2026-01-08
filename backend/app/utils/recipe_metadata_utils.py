"""
Recipe Metadata Utilities

Helper functions for extracting and managing recipe metadata from agent tool outputs.
This allows the conversation manager to track recipes shown to users without re-searching.
"""

import json
import re
from typing import Dict, List, Optional, Any


def extract_recipe_ids_from_tool_output(tool_output: str) -> List[int]:
    """
    Extract recipe IDs from a search tool output.
    
    Args:
        tool_output: The JSON string output from the search tool
        
    Returns:
        List of recipe IDs in the order they were presented
    """
    try:
        # Parse the tool output as JSON first (strict mode)
        data = json.loads(tool_output)

        # Check if it's a search result with recipes
        if isinstance(data, dict) and "results" in data:
            recipe_ids: List[int] = []
            for recipe in data.get("results", []):
                if "id" in recipe:
                    recipe_ids.append(int(recipe["id"]))
            return recipe_ids

        # Check if it's the 'result' field (nested JSON string)
        if isinstance(data, dict) and "result" in data:
            result_str = data.get("result")
            if isinstance(result_str, str):
                # Try to parse nested JSON
                try:
                    nested_data = json.loads(result_str)
                    if isinstance(nested_data, dict) and "results" in nested_data:
                        recipe_ids = []
                        for recipe in nested_data.get("results", []):
                            if "id" in recipe:
                                recipe_ids.append(int(recipe["id"]))
                        return recipe_ids
                except json.JSONDecodeError:
                    # We'll fall back to a more lenient parser below
                    pass

    except json.JSONDecodeError as e:
        # The tool output may be a large/truncated JSON string (as seen in
        # the streaming logs where the "result" field is cut off mid-string).
        # In that case, try a more lenient extraction using a regex that
        # looks for numeric IDs in the text rather than fully parsing JSON.
        id_matches = re.findall(r'"id"\s*:\s*"?(\d+)"?', tool_output)
        if id_matches:
            recipe_ids = []
            seen = set()
            for match in id_matches:
                try:
                    rid = int(match)
                except ValueError:
                    continue
                if rid not in seen:
                    seen.add(rid)
                    recipe_ids.append(rid)

            if recipe_ids:
                return recipe_ids

    except (ValueError, KeyError):
        pass

    return []


def extract_metadata_from_event_stream(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extract recipe metadata from a stream of agent events.
    
    Looks for tool_use events (search tool) and tool_result events to extract
    the actual recipe IDs from the search results.
    
    Args:
        events: List of parsed event dictionaries from the agent stream
        
    Returns:
        Metadata dictionary with recipe_ids and query, or None
    """
    # Map each search tool_use_id to its query and collected recipe IDs,
    # so we can keep the correct order per search and avoid mixing
    # multiple searches together.
    search_order: List[Any] = []  # tool_use_ids in chronological order
    search_queries_by_id: Dict[Any, str] = {}
    recipe_ids_by_search: Dict[Any, List[int]] = {}
    last_search_tool_use_id: Optional[Any] = None

    for event in events:
        event_type = event.get("type")

        # Look for search tool usage to get the query
        if event_type == "tool_use" and event.get("tool_name") == "search":
            tool_input = event.get("tool_input", {})
            search_query = tool_input.get("query_input")
            tool_use_id = event.get("tool_use_id")

            if tool_use_id is not None:
                last_search_tool_use_id = tool_use_id
                if tool_use_id not in search_order:
                    search_order.append(tool_use_id)
                if search_query:
                    search_queries_by_id[tool_use_id] = search_query
                # Ensure we have a list ready for recipe IDs for this search
                recipe_ids_by_search.setdefault(tool_use_id, [])

        # Look for tool results and associate them to the right search
        if event_type == "tool_result":
            content = event.get("content", [])
            tool_use_id = event.get("tool_use_id")

            # Determine which search (if any) this result belongs to
            target_search_id: Optional[Any] = None
            if tool_use_id is not None and tool_use_id in recipe_ids_by_search:
                target_search_id = tool_use_id
            elif last_search_tool_use_id is not None and last_search_tool_use_id in recipe_ids_by_search:
                # Fallback: some tool_result events may omit tool_use_id; assume last search
                target_search_id = last_search_tool_use_id

            if target_search_id is None:
                # Not a search result we care about
                continue

            target_list = recipe_ids_by_search.setdefault(target_search_id, [])

            # Content is typically a list: [{'json': {...}, ...}]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        # Try 'json' field
                        json_content = item.get("json", {})
                        if isinstance(json_content, dict):
                            # Could have 'result' field with JSON string
                            result_field = json_content.get("result")
                            if isinstance(result_field, str):
                                extracted = extract_recipe_ids_from_tool_output(
                                    result_field
                                )
                                if extracted:
                                    target_list.extend(extracted)
                            # Or direct results
                            elif "results" in json_content:
                                for recipe in json_content.get("results", []):
                                    if "id" in recipe:
                                        target_list.append(int(recipe["id"]))

                        # Try 'text' field (alternate format)
                        if "text" in item:
                            extracted = extract_recipe_ids_from_tool_output(
                                item["text"]
                            )
                            if extracted:
                                target_list.extend(extracted)

            # Content might be a string
            elif isinstance(content, str):
                extracted = extract_recipe_ids_from_tool_output(content)
                if extracted:
                    target_list.extend(extracted)

    # Decide which search to report: use the last search in order
    if search_order:
        # Iterate from last to first to find the most recent search with IDs
        for tool_use_id in reversed(search_order):
            ids = recipe_ids_by_search.get(tool_use_id, [])
            if ids:
                query = search_queries_by_id.get(tool_use_id, "")
                return {
                    "type": "search_results",
                    "query": query,
                    "recipe_ids": ids[:10],  # Preserve order, limit to first 10
                    "total_found": len(ids),
                }

        # If we had searches but couldn't extract any IDs, still record the last query
        last_tool_use_id = search_order[-1]
        query = search_queries_by_id.get(last_tool_use_id, "")
        return {
            "type": "search_executed",
            "query": query,
        }

    # No relevant search events found
    return None


def build_recipe_context_prompt(recipe_ids: List[int], query: Optional[str] = None) -> str:
    """
    Build a context prompt section for the agent that includes previously shown recipes.
    
    Args:
        recipe_ids: List of recipe IDs in the order they were shown
        query: Optional search query that produced these results
        
    Returns:
        Formatted context string for the agent
    """
    if not recipe_ids:
        return ""
    
    context_parts = []
    
    if query:
        context_parts.append(f"PREVIOUSLY SHOWN RECIPES (from search: '{query}'):")
    else:
        context_parts.append("PREVIOUSLY SHOWN RECIPES:")
    
    for i, recipe_id in enumerate(recipe_ids, 1):
        context_parts.append(f"  {i}. Recipe ID: {recipe_id}")
    
    context_parts.append("")
    context_parts.append("INSTRUCTION: When the user references 'the second one', 'number 3', 'the first recipe', etc.,")
    context_parts.append("use the corresponding Recipe ID from above. DO NOT perform a new search.")
    context_parts.append("Instead, use the transform tool or fetch details for that specific recipe ID.")
    
    return "\n".join(context_parts)


def parse_recipe_reference(user_message: str) -> Optional[int]:
    """
    Parse a user's reference to a recipe position.
    
    Handles references like:
    - "the second one"
    - "number 3"  
    - "the first recipe"
    - "recipe #2"
    
    Args:
        user_message: The user's message text
        
    Returns:
        The position number (1-indexed), or None if no reference found
    """
    # Normalize to lowercase
    text = user_message.lower()
    
    # Pattern 1: "the second one", "the third", "the first recipe"
    ordinal_map = {
        "first": 1, "1st": 1,
        "second": 2, "2nd": 2,
        "third": 3, "3rd": 3,
        "fourth": 4, "4th": 4,
        "fifth": 5, "5th": 5,
        "sixth": 6, "6th": 6,
        "seventh": 7, "7th": 7,
        "eighth": 8, "8th": 8,
        "ninth": 9, "9th": 9,
        "tenth": 10, "10th": 10,
    }
    
    for ordinal, position in ordinal_map.items():
        if ordinal in text:
            return position
    
    # Pattern 2: "number 3", "recipe number 5", "#3", "recipe 3"
    patterns = [
        r'number\s+(\d+)',
        r'recipe\s+number\s+(\d+)',
        r'#(\d+)',
        r'recipe\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    
    return None


def get_recipe_id_from_reference(
    user_message: str,
    recent_recipe_ids: List[int]
) -> Optional[int]:
    """
    Get the actual recipe ID based on a user's reference.
    
    Args:
        user_message: The user's message (e.g., "show me the second one")
        recent_recipe_ids: List of recipe IDs from recent search results
        
    Returns:
        The actual recipe ID, or None if reference cannot be resolved
    """
    position = parse_recipe_reference(user_message)
    
    if position is not None and recent_recipe_ids:
        # Convert 1-indexed position to 0-indexed
        index = position - 1
        if 0 <= index < len(recent_recipe_ids):
            return recent_recipe_ids[index]
    
    return None
