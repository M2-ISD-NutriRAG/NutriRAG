"""Utility functions for combining vector and BM25 search results using RRF."""

from typing import List, Dict, Any, Tuple


def combine_results(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    top_k: int = 10,
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
    boost_consensus: float = 1.15,
) -> List[Dict[str, Any]]:
    """
    Combine vector search and BM25 search results using Reciprocal Rank Fusion (RRF).

    Args:
        vector_results: List of vector search results with 'COSINE_SIMILARITY_SCORE' and 'ID'
        bm25_results: List of BM25 search results with 'BM25_SCORE' and 'ID'
        top_k: Number of top results to return
        vector_weight: Weight for vector rankings (default 0.7)
        bm25_weight: Weight for BM25 rankings (default 0.3)
        boost_consensus: Boost multiplier for docs in both result sets (default 1.15)

    Returns:
        List of combined results sorted by RRF score
    """
    # Validate inputs
    if not vector_results and not bm25_results:
        return []

    # Normalize weights if they don't sum to 1
    total_weight = vector_weight + bm25_weight
    if total_weight == 0:
        raise ValueError("At least one weight must be positive")

    vector_weight = vector_weight / total_weight
    bm25_weight = bm25_weight / total_weight

    # Sort inputs by their respective scores (descending) to ensure proper ranking
    if vector_results:
        vector_results = sorted(
            vector_results,
            key=lambda x: x["COSINE_SIMILARITY_SCORE"],
            reverse=True,
        )

    if bm25_results:
        bm25_results = sorted(
            bm25_results, key=lambda x: x["BM25_SCORE"], reverse=True
        )

    # RRF constant (k) - controls rank penalty aggressiveness
    # Lower k = more aggressive penalty for lower ranks
    # Typical range: 1-100, default: 60
    k = 60

    # Build rank maps (1-indexed)
    vector_ranks = {}
    for rank, result in enumerate(vector_results, start=1):
        doc_id = result["ID"]
        vector_ranks[doc_id] = rank

    bm25_ranks = {}
    for rank, result in enumerate(bm25_results, start=1):
        doc_id = result["ID"]
        bm25_ranks[doc_id] = rank

    # Get all unique document IDs
    all_doc_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

    # Calculate RRF scores
    rrf_scores = {}

    for doc_id in all_doc_ids:
        score = 0.0

        # Add vector contribution: weight / (k + rank)
        if doc_id in vector_ranks:
            score += vector_weight / (k + vector_ranks[doc_id])

        # Add BM25 contribution: weight / (k + rank)
        if doc_id in bm25_ranks:
            score += bm25_weight / (k + bm25_ranks[doc_id])

        rrf_scores[doc_id] = score

    # Apply consensus boost to documents in both result sets
    for doc_id in rrf_scores:
        if doc_id in vector_ranks and doc_id in bm25_ranks:
            rrf_scores[doc_id] *= boost_consensus

    # Sort by RRF score and get top_k
    sorted_doc_ids = sorted(
        rrf_scores.keys(), key=lambda doc_id: rrf_scores[doc_id], reverse=True
    )[:top_k]

    # Build lookups for document data
    vector_lookup = {r["ID"]: r for r in vector_results}
    bm25_lookup = {r["ID"]: r for r in bm25_results}

    # Build final result set with all document data
    final_results = []

    for doc_id in sorted_doc_ids:
        # Get data from both lookups
        v_data = vector_lookup.get(doc_id, {})
        b_data = bm25_lookup.get(doc_id, {})

        # Merge dictionaries (vector metadata takes precedence)
        result_data = {**b_data, **v_data}

        if result_data:
            # Explicitly ensure both original scores are preserved
            result_data["COSINE_SIMILARITY_SCORE"] = v_data.get(
                "COSINE_SIMILARITY_SCORE"
            )
            result_data["BM25_SCORE"] = b_data.get("BM25_SCORE")
            result_data["COMBINED_SCORE"] = round(rrf_scores[doc_id], 6)

            final_results.append(result_data)

    return final_results
