import os
import sys
import json
import re
from typing import List, Dict, Tuple, TypedDict, Any
from transformers import AutoTokenizer
from tqdm import tqdm

from shared.snowflake.client import SnowflakeClient


class Document(TypedDict):
    doc_id: int
    relevance_score: float


class Query(TypedDict):
    query_text: str
    relevance_documents: List[Document]


def build_prompt(
    prompt_template: str, query_text: str, doc_entries: List[Dict[str, Any]]
) -> str:
    """
    Build a prompt by injecting a query text and document entries.

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

    prompt = prompt_template.replace("{input_query_text}", query_text).replace(
        "{doc_entries}", doc_json
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
    text = text.replace("\\n", "")

    # Remove actual newlines
    text = text.replace("\n", "").replace("\r", "")

    # Remove markdown code blocks
    text = re.sub(r"```(?:json)?", "", text).strip("` ")

    # Remove unwanted ""
    text = text.strip().strip('"').strip("'")

    try:
        parsed = json.loads(text)
        return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    except json.JSONDecodeError:
        text = re.sub(r"\s*:\s*", ":", text)
        text = re.sub(r"\s*,\s*", ",", text)
        text = re.sub(r"\{\s+", "{", text)
        text = re.sub(r"\s+\}", "}", text)
        text = re.sub(r"\[\s+", "[", text)
        text = re.sub(r"\s+\]", "]", text)

        return text.strip()


def get_llm_response(
    client: SnowflakeClient,
    model: str,
    prompt: str,
    response_format: Dict[str, Any],
    temperature: float,
    max_tokens: int,
) -> str:
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

    response_format_json = {"type": "json", "schema": response_format}

    result = client.execute(
        query,
        params=(
            model,
            prompt,
            json.dumps(response_format_json),
            temperature,
            max_tokens,
        ),
        fetch="one",
    )
    return result[0]


def chunk_list_documents(
    documents: List[Dict[str, Any]], chunk_size: int
) -> List[List[Dict[str, Any]]]:
    """
    Chunk a list of documents into smaller lists of a specified size.

    Args:
        documents (List[Dict[str, Any]]): The list of document dictionaries to chunk.
        chunk_size (int): The maximum size of each chunk.

    Returns:
        List[List[Dict[str, Any]]]: A list of document chunks.
    """
    return [documents[i : i + chunk_size] for i in range(0, len(documents), chunk_size)]


def evaluate_documents_with_llm(
    prompt_template: str,
    number_doc_per_call: int,
    llm_model: str,
    llm_model_max_output_token: int,
    llm_json_schema: Dict[str, Any],
    llm_model_temperature: float,
    doc_entries: List[Dict],
    query_text: str,
    max_retries: int = 3,
) -> List[Dict]:
    """
    Process document batches with retry logic for LLM scoring.

    Args:
        doc_entries: List of document entries to score
        query_text: The query text for relevance evaluation
        max_retries: Maximum number of retry attempts per batch

    Returns:
        List of relevance judgments with doc_id, justification, and relevance_score
    """
    relevance_judgments = []

    doc_entries_list_chunks = chunk_list_documents(doc_entries, number_doc_per_call)

    for doc_batch in tqdm(doc_entries_list_chunks, desc="Processing document batches"):
        remaining_docs = doc_batch[:]
        attempt = 0

        while remaining_docs and attempt < max_retries:
            attempt += 1

            prompt = build_prompt(prompt_template, query_text, remaining_docs)

            try:
                llm_response = get_llm_response(
                    client=SnowflakeClient(),
                    model=llm_model,
                    prompt=prompt,
                    response_format=llm_json_schema,
                    temperature=llm_model_temperature,
                    max_tokens=llm_model_max_output_token,
                )

                json_output = json.loads(llm_response)

                # Collect judgments
                for judgment in json_output["relevance_judgments"]:
                    relevance_judgments.append(
                        {
                            "ID": judgment["ID"],
                            "justification": judgment.get("justification", ""),
                            "relevance_score": judgment["relevance_score"],
                        }
                    )

                # Update remaining docs
                processed_ids = {j["ID"] for j in json_output["relevance_judgments"]}
                remaining_docs = [
                    doc for doc in remaining_docs if doc["ID"] not in processed_ids
                ]

                if remaining_docs:
                    print(
                        f"Retry {attempt}/{max_retries} | "
                        f"Missing {len(remaining_docs)} docs for query='{query_text}'"
                    )
                else:
                    print(f"✓ All docs scored for query: {query_text}")
                    break

            except Exception as e:
                print(
                    f"LLM error on retry {attempt} "
                    f"(batch size={len(remaining_docs)})"
                )
                print(e)
                break

        # Add default values for missing docs
        if remaining_docs:
            print(
                f"FINAL MISSING after {max_retries} retries "
                f"for query='{query_text}': {[d['ID'] for d in remaining_docs]}"
            )
            for doc in remaining_docs:
                relevance_judgments.append(
                    {
                        "ID": doc["ID"],
                        "justification": "",
                        "relevance_score": 0.0,
                    }
                )

    return relevance_judgments


if __name__ == "__name__":
    print("This file defines build_prompt and get_llm_response")
