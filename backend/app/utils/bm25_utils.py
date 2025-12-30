import base64
import pickle
import re
from typing import Any, Dict, List, Set, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

# English stop words (hardcoded list)
ENGLISH_STOP_WORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "aren't",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can't",
    "cannot",
    "could",
    "couldn't",
    "did",
    "didn't",
    "do",
    "does",
    "doesn't",
    "doing",
    "don't",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "hadn't",
    "has",
    "hasn't",
    "have",
    "haven't",
    "having",
    "he",
    "he'd",
    "he'll",
    "he's",
    "her",
    "here",
    "here's",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "how's",
    "i",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "if",
    "in",
    "into",
    "is",
    "isn't",
    "it",
    "it's",
    "its",
    "itself",
    "just",
    "k",
    "let's",
    "me",
    "might",
    "more",
    "most",
    "mustn't",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "ought",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "shan't",
    "she",
    "she'd",
    "she'll",
    "she's",
    "should",
    "shouldn't",
    "so",
    "some",
    "such",
    "t",
    "than",
    "that",
    "that's",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "there's",
    "these",
    "they",
    "they'd",
    "they'll",
    "they're",
    "they've",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "wasn't",
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
    "were",
    "weren't",
    "what",
    "what's",
    "when",
    "when's",
    "where",
    "where's",
    "which",
    "while",
    "who",
    "who's",
    "whom",
    "why",
    "why's",
    "with",
    "won't",
    "would",
    "wouldn't",
    "you",
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def tokenize(
    text: str,
    text_fields_to_remove: Set[str] = None,
) -> List[str]:
    """
    Tokenize text with filtering for stop words and column names.

    Converts text to lowercase, extracts word tokens using regex patterns,
    and filters out English stop words and specified field names.

    Args:
        text: Text to tokenize.
        text_fields_to_remove: Set of field names to exclude from tokenization.

    Returns:
        List of filtered tokens with length > 1.
    """

    # Check if text is empty or only whitespace
    if not text.strip():
        return []

    lower_text = text.lower()

    # Extract word tokens using regex: \b\w+\b matches word boundaries and word characters
    tokens = re.findall(r"\b\w+\b", lower_text)

    # Build the set of words to filter (stop words + field names)
    words_to_filter = set()
    words_to_filter.update(ENGLISH_STOP_WORDS)

    if text_fields_to_remove:
        # Add field names to filter set
        words_to_filter.update(field.lower() for field in text_fields_to_remove)

    # Filter out stop words and field names; exclude single-character tokens as they are typically
    # uninformative for search indexing (e.g., "a", "I", "x")
    return [t for t in tokens if t not in words_to_filter and len(t) > 1]


def build_bm25_index(
    documents: List[Dict],
    text_fields: List[str],
    id_field: str = "ID",
    field_weights: Dict[str, int] = None,
) -> Tuple[BM25Okapi, List[Any], List[List[str]]]:
    """
    Build a BM25 index from documents.

    Tokenizes text fields with specified weights and creates a BM25Okapi
    index for relevance ranking. Field weights determine the importance of
    each text field in the final ranking.

    Args:
        documents: List of documents (dictionaries).
        text_fields: List of field names to index.
        id_field: Field name containing unique document identifiers (default: "ID").
        field_weights: Dictionary mapping field names to integer weight values.
            Weights must be integers (default: 1 for all fields).
            Example: {"title": 2, "description": 1} doubles token importance for title.

    Returns:
        Tuple containing:
        - bm25_index: BM25Okapi instance for scoring.
        - doc_ids: List of document identifiers in index order.
        - tokenized_corpus: List of tokenized documents.
    """
    if field_weights is None:
        field_weights = {field: 1 for field in text_fields}

    doc_ids = []
    tokenized_corpus = []

    for doc in documents:
        doc_id = doc.get(id_field)
        if doc_id is None:
            continue

        all_tokens = []

        for field in text_fields:
            text = str(doc.get(field, ""))
            tokens = tokenize(text, text_fields_to_remove=text_fields)

            # Get weight for the field
            weight = field_weights.get(field, 1)

            # Replicate tokens based on field weight for importance in BM25 scoring
            for _ in range(weight):
                all_tokens.extend(tokens)

        if all_tokens:
            doc_ids.append(doc_id)
            tokenized_corpus.append(all_tokens)

    # Create the BM25 index using rank-bm25 library
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, doc_ids, tokenized_corpus


def search_bm25(
    bm25: BM25Okapi, doc_ids: List[Any], query: str, top_k: int = 10
) -> List[Tuple[Any, float]]:
    """
    Perform BM25 search on indexed documents.

    Tokenizes the query and scores all documents using the BM25 algorithm,
    returning the top-k results ranked by relevance.

    Args:
        bm25: BM25Okapi index instance.
        doc_ids: List of document identifiers in index order.
        query: Search query text.
        top_k: Maximum number of results to return (default: 10).

    Returns:
        List of tuples containing (document_id, relevance_score)
        sorted in descending order by score. Empty list if query has no tokens.
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [
        (doc_ids[idx], float(scores[idx]))
        for idx in top_indices
        if scores[idx] > 0
    ]


def serialize_bm25(bm25: BM25Okapi) -> str:
    """
    Serialize BM25 index for persistent storage.

    Converts the BM25Okapi instance to a pickled binary format
    and encodes it as base64 for safe transmission and storage.

    Args:
        bm25: BM25Okapi index instance.

    Returns:
        Base64-encoded string representation of the serialized BM25 index.
    """
    pickled = pickle.dumps(bm25)
    return base64.b64encode(pickled).decode("utf-8")


def deserialize_bm25(serialized: str) -> BM25Okapi:
    """
    Deserialize BM25 index from storage.

    Decodes a base64-encoded string and reconstructs the BM25Okapi
    instance from its pickled binary representation.

    Args:
        serialized: Base64-encoded string representation of the BM25 index.

    Returns:
        Reconstructed BM25Okapi index instance.
    """
    pickled = base64.b64decode(serialized.encode("utf-8"))
    return pickle.loads(pickled)
