import json
import os
import pandas as pd
from tqdm import tqdm
from typing import List, Dict, Tuple, TypedDict, Any

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
        json_schema: Dict[str, any],
        number_doc_per_call: int,
        eval_llm_ground_truth_file_path: str,
        max_retries_llm_calls: int = 3,
    ):
        self.client = client

        self.raw_data_recipes = pd.read_csv(raw_data_file_path)

        # Load ground truth
        with open(query_test_file_path, "r", encoding="utf-8") as f:
            self.ground_truth = json.load(f)

        # Load prompt template
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

        self.llm_model = (llm_model,)
        self.llm_model_context_windows = llm_model_context_windows
        self.llm_model_max_output_token = llm_model_max_output_token
        self.llm_model_temperature = llm_model_temperature
        self.max_retries_llm_calls = max_retries_llm_calls

        self.json_schema = json_schema

        self.number_doc_per_call = number_doc_per_call

        self.eval_llm_ground_truth_file_path = eval_llm_ground_truth_file_path

        self.llm_results = []

    def calculate_llm_relevance_all_queries(self):
        """Calculate LLM relevance for all queries."""

        # add tqdm progress bar
        for query in tqdm(self.ground_truth, desc="Processing queries"):
            query_text = query["query_text"]

            # Build doc entries for the prompt
            doc_entries = []
            for document in query["relevance_documents"]:
                doc_id = document["doc_id"]
                recipe_row = self.raw_data_recipes[
                    self.raw_data_recipes["ID"] == doc_id
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

                doc_entries.append({"doc_id": int(doc_id), "recipe_info": recipe_info})

            # Get relevance judgments from LLM
            relevance_judgments = evaluate_documents_with_llm(
                doc_entries=doc_entries,
                number_doc_per_call=self.number_doc_per_call,
                query_text=query_text,
                prompt_template=self.prompt_template,
                llm_model=self.llm_model,
                llm_model_temperature=self.llm_model_temperature,
                llm_model_max_output_token=self.llm_model_max_output_token,
                json_schema=self.json_schema,
                max_retries=self.max_retries_llm_calls,
            )

            query_doc_relevance_dict = {
                "query_text": query_text,
                "relevance_judgments": relevance_judgments,
            }

            self.llm_results.append(query_doc_relevance_dict)

    def main(self):
        """Main method to run the evaluation"""
        self.calculate_llm_relevance_all_queries()

        coherence_avg_per_query, per_query_scores = compare_ground_truth_vs_llm(
            ground_truth=self.ground_truth,
            llm_results=self.llm_results,
        )
        print(f"Overall coherence score: {coherence_avg_per_query}")

        self.llm_results.append({"COHERENCE_SCORE_AVG_QUERY": coherence_avg_per_query})

        with open(self.eval_llm_ground_truth_file_path, "w", encoding="utf-8") as f:
            json.dump(self.llm_results, f, indent=4)
