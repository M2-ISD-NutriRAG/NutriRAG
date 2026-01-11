import json
import os
import pandas as pd
from tqdm import tqdm
from typing import List, Dict, Tuple, TypedDict, Any
import pdb

from shared.snowflake.client import SnowflakeClient
from experiments.utils.llm import evaluate_documents_with_llm
from experiments.utils.metrics import compare_ground_truth_vs_llm


class EvalLLMJudge:
    def __init__(
        self,
        client: SnowflakeClient,
        raw_data_file_path: str,
        query_test_file_path: str,
        prompt_file_path: str,
        llm_model: str,
        llm_model_context_windows: int,
        llm_model_max_output_token: int,
        llm_model_temperature: float,
        llm_json_schema: Dict[str, any],
        number_doc_per_call: int,
        eval_llm_ground_truth_file_path: str,
        max_retries_llm_calls: int = 3,
        override_llm_eval: bool = False,
    ):
        self.client = client

        self.raw_data_recipes = pd.read_csv(raw_data_file_path)

        # Load ground truth
        with open(query_test_file_path, "r", encoding="utf-8") as f:
            self.ground_truth_dict = {
                query: {int(doc_id): score for doc_id, score in doc_scores.items()}
                for query, doc_scores in json.load(f).items()
            }

        # Load prompt template
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

        self.llm_model = llm_model
        self.llm_model_context_windows = llm_model_context_windows
        self.llm_model_max_output_token = llm_model_max_output_token
        self.llm_model_temperature = llm_model_temperature
        self.max_retries_llm_calls = max_retries_llm_calls

        self.llm_json_schema = llm_json_schema

        self.number_doc_per_call = number_doc_per_call

        self.eval_llm_ground_truth_file_path = eval_llm_ground_truth_file_path

        self.llm_results_dict = {}

        self.override_llm_eval = override_llm_eval

    def calculate_llm_relevance_all_queries(self):
        """Calculate LLM relevance for all queries."""

        if os.path.exists(self.eval_llm_ground_truth_file_path) and not (
            self.override_llm_eval
        ):
            print(
                f"LLM evaluation file {self.eval_llm_ground_truth_file_path} already exists. Skipping LLM evaluation."
            )
            with open(self.eval_llm_ground_truth_file_path, "r", encoding="utf-8") as f:
                self.llm_results_file_dict = json.load(f)
                self.llm_results_dict = {
                    query: {
                        int(doc_id): {
                            "relevance_score": relevance_score_justification.get(
                                "relevance_score", 0.0
                            ),
                            "justification": relevance_score_justification.get(
                                "justification", ""
                            ),
                        }
                        for doc_id, relevance_score_justification in doc_scores.items()
                    }
                    for query, doc_scores in self.llm_results_file_dict.items()
                    if isinstance(doc_scores, dict)
                }
            return

        for query in tqdm(self.ground_truth_dict, desc="Processing queries"):

            print("query", query)

            # Build doc entries for the prompt
            doc_entries = []
            for document_id in self.ground_truth_dict[query].keys():
                recipe_row = self.raw_data_recipes[
                    self.raw_data_recipes["ID"] == int(document_id)
                ]
                if recipe_row.empty:
                    continue

                recipe_info = {}
                for col_name in self.raw_data_recipes.columns:
                    value = recipe_row.iloc[0][col_name]
                    if hasattr(value, "item"):
                        recipe_info[col_name] = value.item()
                    else:
                        recipe_info[col_name] = value

                doc_entries.append({"ID": int(document_id), "recipe_info": recipe_info})

            # Get relevance judgments from LLM
            relevance_judgments = evaluate_documents_with_llm(
                doc_entries=doc_entries,
                number_doc_per_call=self.number_doc_per_call,
                query_text=query,
                prompt_template=self.prompt_template,
                llm_model=self.llm_model,
                llm_model_temperature=self.llm_model_temperature,
                llm_model_max_output_token=self.llm_model_max_output_token,
                llm_json_schema=self.llm_json_schema,
                max_retries=self.max_retries_llm_calls,
            )

            self.llm_results_dict.setdefault(query, {})

            for doc in relevance_judgments:
                self.llm_results_dict[query][doc["ID"]] = {
                    "relevance_score": float(doc.get("relevance_score", 0.0)),
                    "justification": doc.get("justification", ""),
                }

    def main(self):
        """Main method to run the evaluation"""
        self.calculate_llm_relevance_all_queries()

        coherence_avg_per_query, per_query_scores = compare_ground_truth_vs_llm(
            ground_truth=self.ground_truth_dict,
            llm_results=self.llm_results_dict,
        )
        print(f"Overall coherence score: {coherence_avg_per_query}")

        self.llm_results_dict["COHERENCE_SCORE_AVG_QUERY"] = coherence_avg_per_query

        with open(self.eval_llm_ground_truth_file_path, "w", encoding="utf-8") as f:
            json.dump(self.llm_results_dict, f, indent=4)
