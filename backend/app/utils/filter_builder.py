"""Utility functions for building Snowflake SQL filter conditions."""

from typing import Optional, Dict, Any

try:
    from app.models.search import SearchFilters
except (ImportError, ModuleNotFoundError):
    from search import SearchFilters


def build_filter_conditions(filters: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Build Snowflake SQL WHERE clause from filter dictionary.

    Validates the filter dictionary against SearchFilters model first.

    Expected filter structure:
    {
        "numeric_filters": [
            {"name": "minutes", "operator": "<=", "value": 30},
            ...
        ],
        "dietary_filters": ["vegan", "gluten_free"],
        "include_ingredients": ["tomato", "basil"],
        "exclude_ingredients": ["nuts"],
        "any_ingredients": ["cheese", "milk"]
    }

    Args:
        filters: Dictionary containing various filter criteria

    Returns:
        SQL WHERE clause (without "WHERE" keyword) or None if no filters

    Raises:
        ValueError: If filters don't validate against SearchFilters model
    """
    if not filters:
        return None

    # Validate against SearchFilters model
    try:
        validated = SearchFilters(**filters)
    except Exception as e:
        raise ValueError(f"Invalid filter structure: {str(e)}")

    conditions = []

    # 1. Numeric filters (minutes, n_steps, servings, etc.)
    numeric_filters = filters.get("numeric_filters", [])
    if numeric_filters:
        for num_filter in numeric_filters:
            field = num_filter.get("name", "").upper()
            operator = num_filter.get("operator", "")
            value = num_filter.get("value")

            if field and operator and value is not None:
                conditions.append(f"{field} {operator} {value}")

    # 2. Dietary filters (filters column) - must contain all (exact match)
    dietary_filters = filters.get("dietary_filters", [])
    if dietary_filters:
        for tag in dietary_filters:
            safe_tag = str(tag).replace("'", "''")
            conditions.append(f"ARRAY_CONTAINS('{safe_tag}'::VARIANT, FILTERS)")

    # 3. Include ingredients - must contain all (fuzzy match with FILTER)
    include_ingredients = filters.get("include_ingredients", [])
    if include_ingredients:
        for ingredient in include_ingredients:
            safe_ingredient = str(ingredient).replace("'", "''").lower()
            # Use ARRAY_SIZE with FILTER for partial matching
            conditions.append(
                f"ARRAY_SIZE(FILTER(INGREDIENTS, x -> CONTAINS(LOWER(x::STRING), '{safe_ingredient}'))) > 0"
            )

    # 4. Exclude ingredients - must not contain any (fuzzy match with FILTER)
    exclude_ingredients = filters.get("exclude_ingredients", [])
    if exclude_ingredients:
        for ingredient in exclude_ingredients:
            safe_ingredient = str(ingredient).replace("'", "''").lower()
            # Use ARRAY_SIZE with FILTER for partial matching - must be 0
            conditions.append(
                f"ARRAY_SIZE(FILTER(INGREDIENTS, x -> CONTAINS(LOWER(x::STRING), '{safe_ingredient}'))) = 0"
            )

    # 5. Any ingredients - at least one must be present (fuzzy match with FILTER)
    any_ingredients = filters.get("any_ingredients", [])
    if any_ingredients:
        any_conditions = []
        for ingredient in any_ingredients:
            safe_ingredient = str(ingredient).replace("'", "''").lower()
            any_conditions.append(
                f"ARRAY_SIZE(FILTER(INGREDIENTS, x -> CONTAINS(LOWER(x::STRING), '{safe_ingredient}'))) > 0"
            )
        if any_conditions:
            conditions.append(f"({' OR '.join(any_conditions)})")

    # Combine all conditions with AND
    if conditions:
        return " AND ".join(conditions)

    return None
