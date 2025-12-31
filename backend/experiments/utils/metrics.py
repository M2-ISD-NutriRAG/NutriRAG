from typing import List, Dict, Tuple, TypedDict, Any


class Document(TypedDict):
    doc_id: int
    relevance_score: float


class Query(TypedDict):
    query_text: str
    relevance_documents: List[Document]


def compare_ground_truth_vs_llm(
    ground_truth: List[Query], llm_results: List[Query]
) -> Tuple[float, float, List[float]]:
    """
    Computes how close LLM relevance scores are to the ground truth.

    Args:
        ground_truth (Dict[str, list]): Dictionary mapping each query to a list of relevant documents.
            Each document is a dict containing:
            {
                "query_text": "a vegan dessert that require minimum time to prepare",
                "relevance_judgments": [
                {
                    "doc_id": 515586,
                    "relevance_score": 1
                }
                ]
            },
        llm_results (Dict[str, list]): Dictionary mapping each query to a list of LLM relevance judgments.
            Each document is a dict containing:
            {
                "query_text": "a vegan dessert that require minimum time to prepare",
                "relevance_judgments": [
                {
                    "doc_id": 515586,
                    "relevance_score": 1,
                    "justification": "..."
                }
                ]
            },

    Returns:
        Tuple[float, float, List[float]]:
            - Overall average similarity score across all queries (float between 0 and 1).
            - List of per-query similarity scores (float between 0 and 1).
    """
    query_diffs = []
    doc_diffs = []

    for gt_query, llm_query in zip(ground_truth, llm_results):

        gt_scores = {
            d["doc_id"]: d["relevance_score"] for d in gt_query["relevance_documents"]
        }
        llm_scores = {
            d["doc_id"]: d["relevance_score"] for d in llm_query["relevance_judgments"]
        }

        all_doc_ids = set(gt_scores.keys()) | set(llm_scores.keys())

        diffs = []
        for doc_id in all_doc_ids:
            gt = gt_scores.get(doc_id, 0)  # missing → assume 0
            llm = llm_scores.get(doc_id, 0)
            diff = 1 - abs(gt - llm)
            diffs.append(diff)
            doc_diffs.append(diff)

        query_avg = sum(diffs) / len(diffs)
        query_diffs.append(query_avg)

    # score per query and overall
    final_score_query = sum(query_diffs) / len(query_diffs)

    return final_score_query, query_diffs


if __name__ == "__main__":
    print("This file defines functions required to compute metrics")
