from typing import List, Dict, Tuple, TypedDict, Any
import pdb


def compare_ground_truth_vs_llm(
    ground_truth: Dict[str, Dict[int, float]],
    llm_results: Dict[str, Dict[int, Dict[str, Any]]],
) -> Tuple[float, float, List[float]]:
    """
    Computes how close LLM relevance scores are to the ground truth.

    Args:
        ground_truth (Dict[str, Dict[int, float]]): Dictionary mapping each query to a dictionary of relevant documents and their relevance scores.
        llm_results (Dict[str, Dict[int, Dict[str, Any]]]): Dictionary mapping each query to a dictionary of documents and their LLM-assigned relevance scores.
            Each document is represented as:
            {
                "a vegan dessert that require minimum time to prepare" :
                {
                    515586 : 1,
                    123456 : 0.5,
                    ...
                }
            },
        llm_results (Dict[str, list]): Dictionary mapping each query to a list of LLM relevance judgments.
            Each document is a dict containing:
            {
                "a vegan dessert that require minimum time to prepare" :
                {
                    515586 : {"relevance_score": 1, "justification": "..."},
                    123456 : {"relevance_score": 0.25, "justification": "..."},
                    ...
                }
            },

    Returns:
        Tuple[float, float, List[float]]:
            - Overall average similarity score across all queries (float between 0 and 1).
            - List of per-query similarity scores (float between 0 and 1).
    """
    query_diffs = []
    doc_diffs = []

    for gt_query, llm_query in zip(ground_truth, llm_results):

        gt_scores = {id: score for id, score in ground_truth[gt_query].items()}
        llm_scores = {
            id: score["relevance_score"] for id, score in llm_results[llm_query].items()
        }

        all_IDs = set(gt_scores.keys()) & set(llm_scores.keys())

        diffs = []
        for ID in all_IDs:
            gt = gt_scores.get(ID, 0)
            llm = llm_scores.get(ID, 0)
            diff = 1 - abs(gt - llm)
            diffs.append(diff)
            doc_diffs.append(diff)

        query_avg = sum(diffs) / len(diffs) if diffs else 0.0
        query_diffs.append(query_avg)

    # score per query and overall
    final_score_query = sum(query_diffs) / len(query_diffs)

    return final_score_query, query_diffs


def calculate_precision_at_k(retrieved_docs, k):
    """Calculate Precision@K."""
    if k == 0:
        return 0.0
    relevant_count = sum(doc["relevance_score"] for doc in retrieved_docs[:k])
    return relevant_count / k


def calculate_recall_at_k(retrieved_docs, expected_relevant_docs, k):
    """Calculate Recall@K."""
    if k == 0:
        return 0.0

    total_relevant_in_pool = sum(
        info["relevance_score"] for info in expected_relevant_docs.values()
    )

    if total_relevant_in_pool == 0:
        return 0.0

    relevant_count = sum(doc["relevance_score"] for doc in retrieved_docs[:k])

    return relevant_count / total_relevant_in_pool


def calculate_ap_at_k(retrieved_docs, k):
    """Calculate Average Precision@K."""
    relevant_count = 0
    sum_precisions = 0.0

    for i, doc in enumerate(retrieved_docs[:k], 1):
        if doc["relevance_score"] <= 0.5:
            continue
        relevant_count += doc["relevance_score"]
        precision_at_i = relevant_count / i
        sum_precisions += precision_at_i

    if relevant_count == 0:
        return 0.0
    return sum_precisions / relevant_count


def calculate_ndcg_at_k(retrieved_docs, k):
    """Calculate Normalized Discounted Cumulative Gain@K."""

    def dcg(relevances, k):
        dcg_sum = 0.0
        for i, rel in enumerate(relevances[:k], 1):
            dcg_sum += rel / np.log2(i + 1)
        return dcg_sum

    relevances = [doc["relevance_score"] for doc in retrieved_docs]
    ideal_relevances = sorted(relevances, reverse=True)

    dcg_score = dcg(relevances, k)
    idcg_score = dcg(ideal_relevances, k)

    if idcg_score == 0:
        return 0.0
    return dcg_score / idcg_score


def calculate_mrr_at_k(retrieved_docs, k):
    """Calculate Mean Reciprocal Rank@K."""
    for i, doc in enumerate(retrieved_docs[:k], 1):
        if doc["relevance_score"] == 1:
            return 1.0 / i
    return 0.0


if __name__ == "__main__":
    print("This file defines functions required to compute metrics")
