import os
import sys
import json
import re
from typing import List, Dict, Tuple, TypedDict, Any
from transformers import AutoTokenizer

from shared.snowflake.client import SnowflakeClient

class Document(TypedDict):
    doc_id: int
    relevance_score: float
    
class Query(TypedDict):
    query_text: str
    relevance_documents: List[Document]


def count_number_tokens(client: SnowflakeClient, model: str,  text: str) -> int:
    """Count the number of token in a given text

    Args:
        client (SnowflakeClient): SnowflakeClient instance
        text (str): the prompt

    Returns:
        int: the number of token in that prompt
    """
    
    query = """
        SELECT SNOWFLAKE.CORTEX.COUNT_TOKENS(
            %s,
            %s
        ) AS response;
    """
    
    result = client.execute(
        query, 
        params=(model, text), 
        fetch="one"
    )
    
    return result[0]


def build_prompt(prompt_template: str, query_text: str, doc_entries: List[Dict[str, Any]]) -> str:
    """
    Build a prompt by safely injecting a query text and document entries.

    Args:
        prompt_template (str): the base prompt
        query_text (str): The user's query text to include in the prompt.
        doc_entries (List[Dict[str, Any]]): A list of document entries. Each entry is a dictionary with the structure:
            {
                "doc_id": 1,
                "recipe_info": {
                    Name: Cheesckake,
                    Description: A wonderfull ... ,
                    ...
                }
            }
            This list will be converted to JSON and inserted into the prompt.

    Returns:
        str: The final prompt string with `query_text` and `doc_entries` safely inserted.
    """
    doc_json = json.dumps(doc_entries, indent=2, ensure_ascii=False)

    prompt = (
        prompt_template
        .replace("{input_query_text}", query_text)
        .replace("{doc_entries}", doc_json)
    )

    return normalize_json_response(prompt)

def normalize_json_response(text: str) -> str:
    """
    Normalize JSON response to compact single line, preserving spaces inside string values.
    
    Args:
        text (str): Raw JSON string from LLM (may contain \n, extra spaces, etc.)
        
    Returns:
        str: Compact, single-line JSON string
    """
    # Remove all literal \n escape sequences
    text = text.replace('\\n', '')
    
    # Remove actual newlines
    text = text.replace('\n', '').replace('\r', '')
    
    # Remove markdown code blocks
    text = re.sub(r'```(?:json)?', '', text).strip('` ')
    
    # Remove unwanted ""
    text = text.strip().strip('"').strip("'")
    
    try:
        parsed = json.loads(text)
        return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
    except json.JSONDecodeError:
        text = re.sub(r'\s*:\s*', ':', text)
        text = re.sub(r'\s*,\s*', ',', text)
        text = re.sub(r'\{\s+', '{', text)
        text = re.sub(r'\s+\}', '}', text)
        text = re.sub(r'\[\s+', '[', text)
        text = re.sub(r'\s+\]', ']', text)
        
        return text.strip()


def split_docs_recursively(client: SnowflakeClient,
                           model: str,
                           max_tokens: int,
                           base_template_size: int,
                           doc_entries: List[Dict[str, Any]]) -> List[List[Dict]]:
    """
    Recursively split documents in half until they fit within max_tokens.
    """
    
    num_token_doc = count_number_tokens(client=client, model=model, text=str(doc_entries))
    
    if base_template_size + num_token_doc > max_tokens:
        mid = len(doc_entries) // 2
        left_half = doc_entries[:mid]
        right_half = doc_entries[mid:]
    else:
        return [doc_entries]
    
    if len(doc_entries) == 1:
        return [doc_entries]
        
    # Recursively split both halves
    left_batches = split_docs_recursively(client, model, max_tokens, base_template_size, left_half)
    right_batches = split_docs_recursively(client, model, max_tokens, base_template_size, right_half)
    
    return left_batches + right_batches


def get_llm_response(client: SnowflakeClient, 
                     model: str, 
                     prompt: str, 
                     response_format: Dict[str, Any],
                     temperature: float,
                     max_tokens: int) -> str:
    """
    Query Snowflake LLM with JSON schema for structured output.
    
    Args:
        client (SnowflakeClient): SnowflakeClient instance
        model (str): Model name (e.g., 'mistral-large2')
        prompt (str): The prompt text
        response_format (Dict[str, Any]): JSON schema dict
        
    Returns:
        str: JSON response from LLM
    """
    
    query = """
        SELECT AI_COMPLETE(
            model => %s,
            prompt => %s,
            response_format => PARSE_JSON(%s),
            model_parameters => {
                'temperature': %s,
                'max_tokens': %s
    }
        ) AS response;
    """
    
    response_format_json = {
        'type': 'json',
        'schema': response_format
    }
    
    result = client.execute(
        query, 
        params=(model, 
                prompt, 
                json.dumps(response_format_json),
                temperature,
                max_tokens), 
        fetch="one"
    )
    return result[0]


def compare_ground_truth_vs_llm(
    ground_truth: List[Query],
    llm_results: List[Query]
) -> Tuple[float, List[float]]:
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
        Tuple[float, List[float]]: 
            - Overall average similarity score across all queries (float between 0 and 1).
            - List of per-query similarity scores (float between 0 and 1).
    """
    query_diffs = []

    for gt_query, llm_query in zip(ground_truth, llm_results):

        gt_scores = {d["doc_id"]: d["relevance_score"] for d in gt_query["relevance_documents"]}
        llm_scores = {d["doc_id"]: d["relevance_score"] for d in llm_query["relevance_judgments"]}

        all_doc_ids = set(gt_scores.keys()) | set(llm_scores.keys())

        diffs = []
        for doc_id in all_doc_ids:
            gt = gt_scores.get(doc_id, 0)   # missing → assume 0
            llm = llm_scores.get(doc_id, 0)
            diffs.append(1 - abs(gt - llm))

        query_diffs.append(sum(diffs) / len(diffs))

    final_score = sum(query_diffs) / len(query_diffs)
    return final_score, query_diffs

if __name__ == '__name__':
    print("This file defines build_prompt and get_llm_response")
    

