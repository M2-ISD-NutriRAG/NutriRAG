import re


def clean_columns_to_embedd(tag_value: any, col_name: str) -> str:
    """
    Format text of the columns used for embedding

    Args:
        tag_value (any): The input value to clean. Can be a string, list, number, or None.
                        Will be converted to string before processing.
        col_name (str): The label/prefix to add before the cleaned text
                       (e.g., "NAME", "TAGS", "INGREDIENTS").

    Returns:
        str: Cleaned and formatted text in the format "{col_name}: {cleaned_text}."
             Returns empty string if input is None or empty.
    """

    if tag_value is None or tag_value == "":
        return ""

    text = str(tag_value)

    # Remove list brackets and quotes
    text = re.sub(r"[\[\]'\"]", "", text)

    text = text.replace("|", ",")

    # Convert to lowercase
    text = text.lower()

    # Keep only alphanumeric, spaces, and . , ? !
    text = re.sub(r"[^a-z0-9 .,?!]+", "", text)

    # Remove excess spaces
    text = re.sub(r" +", " ", text)

    # Remove spaces before commas
    text = re.sub(r" ,", ",", text)

    # Clean up spaces around punctuation
    text = text.strip()

    # Return formatted text
    return f"{col_name}: {text}."
