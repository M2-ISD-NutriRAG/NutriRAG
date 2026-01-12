import json
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Tuple, TypedDict, Any
import pdb

from shared.snowflake.client import SnowflakeClient
from experiments.utils.llm import evaluate_documents_with_llm
from experiments.utils.calculate_embedding import (
    load_embedding_models,
    retrieve_documents,
)
from experiments.utils.metrics import (
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_ap_at_k,
    calculate_ndcg_at_k,
    calculate_mrr_at_k,
)


class EvalEmbeddingModels:
    def __init__(
        self,
        client: SnowflakeClient,
        embedding_data_file_path: str = None,
        data_columns: List[str] = [
            "NAME",
            "TAGS",
            "INGREDIENTS",
            "STEPS",
            "DESCRIPTION",
        ],
        id_column: str = "ID",
        eval_query_test_file_path: str = None,
        ground_truth_file_path: str = None,
        eval_with_llm_or_ground_truth: str = "llm",
        embedding_model_list: List[str] = [],
        prompt_file_path: str = None,
        llm_model: str = "mistral-large2",
        llm_model_context_windows: int = 64000,
        llm_model_max_output_token: int = 8192,
        llm_model_temperature: float = 0.0,
        llm_json_schema: Dict[str, any] = None,
        number_doc_per_call: int = 20,
        max_retries_llm_calls: int = 3,
        top_k: List[int] = [1, 5, 10],
        output_retrived_documents_file_path: str = None,
        output_retrived_documents_relevance_file_path: str = None,
        output_topk_model_query_retrieved_documents_relevance_file_path: str = None,
        output_retrived_documents_metrics_file_path: str = None,
        output_retrived_documents_aggregated_metrics_file_path: str = None,
        override_documents_retrival: bool = False,
        override_embedding_eval: bool = False,
    ):

        self.client = client or SnowflakeClient()

        self.eval_with_llm_or_ground_truth = eval_with_llm_or_ground_truth

        # load embedding data
        self.df_recipes_embedding = pd.read_csv(embedding_data_file_path)

        # data columns and id column
        self.data_columns = data_columns
        self.id_column = id_column

        if "llm" in self.eval_with_llm_or_ground_truth.lower():
            with open(eval_query_test_file_path, "r", encoding="utf-8") as f:
                self.ground_truth_dict = {item: {} for item in json.load(f)}
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()

            print("loaded queries and prompt template for LLM evaluation.")

            self.output_retrived_query_documents_relevance_file_path = (
                output_retrived_documents_relevance_file_path
            )

            # model parameters
            self.llm_model = llm_model
            self.llm_model_context_windows = llm_model_context_windows
            self.llm_model_max_output_token = llm_model_max_output_token
            self.llm_model_temperature = llm_model_temperature
            self.max_retries_llm_calls = max_retries_llm_calls
            self.llm_json_schema = llm_json_schema
            self.number_doc_per_call = number_doc_per_call

        if "ground_truth" in self.eval_with_llm_or_ground_truth.lower():
            with open(ground_truth_file_path, "r", encoding="utf-8") as f:
                self.ground_truth_dict = json.load(f)
            print("Loaded ground truth data for evaluation.")

        # output_files
        self.output_retrived_documents_file_path = output_retrived_documents_file_path
        self.output_topk_model_query_retrieved_documents_relevance_file_path = (
            output_topk_model_query_retrieved_documents_relevance_file_path
        )
        self.output_retrived_documents_metrics_file_path = (
            output_retrived_documents_metrics_file_path
        )
        self.output_retrived_documents_aggregated_metrics_file_path = (
            output_retrived_documents_aggregated_metrics_file_path
        )

        self.embedding_model_list = embedding_model_list
        self.top_k = top_k

        self.retrived_model_query_docs_dict = (
            {}
        )  # retrived documents dict per top_k, model, config, query
        self.query_retrived_docs_dict = {}  # retrived documents per query dict

        self.retrived_model_query_docs_metrics_list = (
            []
        )  # metrics list per top k, model, config, query

        self.override_documents_retrival = override_documents_retrival
        self.override_embedding_eval = override_embedding_eval

    def load_embeddings(self):
        """Load embeddings from the cache file."""

        emb_columns = [
            col for col in self.df_recipes_embedding.columns if col.endswith("_EMB")
        ]
        print(f"Found embedding columns: {emb_columns}")

        for col in emb_columns:
            self.df_recipes_embedding[col] = self.df_recipes_embedding[col].apply(
                lambda x: np.fromstring(x.strip("[]"), sep=" ", dtype=np.float32)
            )

        for col in emb_columns:
            print(
                f"{col} -> first embedding shape: {self.df_recipes_embedding[col][0].shape}"
            )

    def calculate_retrived_documents(self):
        """retrive documents for each top_k, embedding model, configuration and query"""

        # Check if the file exists
        if os.path.exists(self.output_retrived_documents_file_path) and not (
            self.override_documents_retrival
        ):
            print(
                f"Loading cached results from {self.output_retrived_documents_file_path} ..."
            )
            with open(
                self.output_retrived_documents_file_path, "r", encoding="utf-8"
            ) as f:
                self.retrived_model_query_docs_dict = json.load(f)

            return

        # load embedding models
        embedding_model_dict = load_embedding_models(self.embedding_model_list)

        embeddings_cols = [
            col for col in self.df_recipes_embedding.columns if col.endswith("_EMB")
        ]

        print(
            f"Calculating retrived documents for all combinaison of top_k, models, columns configurations and queries..."
        )

        for k in tqdm(self.top_k, desc="Top K values"):
            for emb_col in tqdm(
                embeddings_cols, desc="(model, Embedding) configurations"
            ):
                # Convert embedding column to a list of numpy arrays
                documents = self.df_recipes_embedding[emb_col].tolist()

                for query in self.ground_truth_dict:

                    # Build model name + config name from column name
                    model_name = "/".join(emb_col.split("/")[:-1])
                    config_name = emb_col.split("/")[-1].replace("_EMB", "")

                    model = embedding_model_dict[model_name]

                    retrieved_documents_list = retrieve_documents(
                        query=query,
                        model=model,
                        documents=documents,
                        df=self.df_recipes_embedding,
                        columns_to_select=[self.id_column] + self.data_columns,
                        top_k=k,
                    )

                    self.retrived_model_query_docs_dict.setdefault(k, {}).setdefault(
                        model_name, {}
                    ).setdefault(config_name, {})[query] = retrieved_documents_list

        # Save to file for future runs
        with open(self.output_retrived_documents_file_path, "w", encoding="utf-8") as f:
            json.dump(self.retrived_model_query_docs_dict, f, indent=4)

    def get_query_retrived_documents(self):
        """Create a dictionary of retrieved documents for each query."""

        seen = {}

        for k_dict in self.retrived_model_query_docs_dict.values():
            for model_dict in k_dict.values():
                for config_dict in model_dict.values():
                    for query, docs in config_dict.items():
                        for doc in docs:
                            clean_doc = {
                                col: doc[col]
                                for col in [self.id_column] + self.data_columns
                            }
                            doc_id = clean_doc[self.id_column]

                            if doc_id in seen.get(query, set()):
                                continue

                            seen.setdefault(query, set()).add(doc_id)

                            self.query_retrived_docs_dict.setdefault(query, []).append(
                                clean_doc
                            )

    def calculate_retrived_documents_relevance(self):
        """calculate relevance of documents retrived for each query"""

        # Check if the file exists
        if (
            os.path.exists(self.output_retrived_query_documents_relevance_file_path)
            and not (self.override_documents_retrival)
            and not (self.override_embedding_eval)
        ):
            print(
                f"Loading cached results from {self.output_retrived_query_documents_relevance_file_path} ..."
            )
            with open(
                self.output_retrived_query_documents_relevance_file_path,
                "r",
                encoding="utf-8",
            ) as f:
                self.ground_truth_dict = json.load(f)

            self.ground_truth_dict = {
                query: {int(doc_id): score for doc_id, score in doc_scores.items()}
                for query, doc_scores in self.ground_truth_dict.items()
                if isinstance(doc_scores, dict)
            }
            return

        print("Calculating relevance scores using LLM...")

        for query in tqdm(
            self.query_retrived_docs_dict,
            desc="Processing queries",
        ):

            # Build doc entries for the prompt
            doc_entries = []
            for document in self.query_retrived_docs_dict[query]:
                doc_id = document[self.id_column]
                recipe_row = self.df_recipes_embedding[
                    self.df_recipes_embedding[self.id_column] == doc_id
                ]
                if recipe_row.empty:
                    continue

                recipe_info = {}
                for col_name in self.data_columns:
                    value = recipe_row.iloc[0][col_name]
                    if hasattr(value, "item"):
                        recipe_info[col_name] = value.item()
                    else:
                        recipe_info[col_name] = value

                doc_entries.append(
                    {self.id_column: int(doc_id), "recipe_info": recipe_info}
                )

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

            self.ground_truth_dict.setdefault(query, {})

            for doc in relevance_judgments:
                self.ground_truth_dict[query][doc["ID"]] = {
                    "relevance_score": float(doc.get("relevance_score", 0.0)),
                    "justification": doc.get("justification", ""),
                }

        with open(
            self.output_retrived_query_documents_relevance_file_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.ground_truth_dict, f, indent=4)

    def map_documents_relevance_to_retrived_documents(self):
        """Map relevance scores back to the retrived documents."""

        for k, model_dict in self.retrived_model_query_docs_dict.items():
            for model_name, config_dict in model_dict.items():
                for config_name, query_dict in config_dict.items():
                    for query, docs in query_dict.items():

                        for doc in docs:
                            doc_id = doc.get("ID")

                            # Get the relevance info (dict with score and justification)
                            relevance_info = self.ground_truth_dict.get(query, {}).get(
                                doc_id, {"relevance_score": 0.0, "justification": ""}
                            )

                            # attach relevance score if available
                            doc["relevance_score"] = relevance_info.get(
                                "relevance_score", 0.0
                            )
                            doc["justification"] = relevance_info.get(
                                "justification", ""
                            )

        with open(
            self.output_topk_model_query_retrieved_documents_relevance_file_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.retrived_model_query_docs_dict, f, indent=4)

    def evaluate_retrieval(self):
        """Evaluate retrieval metrics for all models, configs, and queries."""

        for (
            k,
            models_data,
        ) in self.retrived_model_query_docs_dict.items():
            k_value = int(k)

            for model_name, configs_data in models_data.items():
                for config_name, queries_data in configs_data.items():
                    for query_string, retrieved_docs in queries_data.items():

                        expected_retrived_docs = self.ground_truth_dict[query_string]

                        precision = calculate_precision_at_k(retrieved_docs, k_value)
                        recall = calculate_recall_at_k(
                            retrieved_docs, expected_retrived_docs, k_value
                        )
                        ap = calculate_ap_at_k(retrieved_docs, k_value)
                        ndcg = calculate_ndcg_at_k(retrieved_docs, k_value)
                        mrr = calculate_mrr_at_k(retrieved_docs, k_value)

                        self.retrived_model_query_docs_metrics_list.append(
                            {
                                "k": k_value,
                                "model": model_name,
                                "config": config_name,
                                "query": query_string,
                                "precision@k": precision,
                                "recall@k": recall,
                                "MAP@k": ap,
                                "NDCG@k": ndcg,
                                "MRR@k": mrr,
                            }
                        )

        with open(
            self.output_retrived_documents_metrics_file_path, "w", encoding="utf-8"
        ) as f:
            json.dump(self.retrived_model_query_docs_metrics_list, f, indent=4)

    def aggregate_metrics(self):
        """Aggregate metrics across queries for each (model, config, k) combination."""

        df = pd.DataFrame(self.retrived_model_query_docs_metrics_list)

        grouped = (
            df.groupby(["k", "model", "config"])
            .agg(
                {
                    "precision@k": "mean",
                    "recall@k": "mean",
                    "MAP@k": "mean",  # Mean Average Precision across queries
                    "NDCG@k": "mean",
                    "MRR@k": "mean",
                }
            )
            .reset_index()
        )

        self.retrived_model_query_docs_metrics_agg_dict = grouped.to_dict(
            orient="records"
        )

        # Save as list of records (flat structure)
        with open(
            self.output_retrived_documents_aggregated_metrics_file_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.retrived_model_query_docs_metrics_agg_dict, f, indent=4)

    def main(self):
        """Main method to evaluate embedding models using LLM judge."""

        self.load_embeddings()
        self.calculate_retrived_documents()
        self.get_query_retrived_documents()

        print("Evaluation method:", self.eval_with_llm_or_ground_truth)

        if "llm" in self.eval_with_llm_or_ground_truth.lower():
            self.calculate_retrived_documents_relevance()

        self.map_documents_relevance_to_retrived_documents()
        self.evaluate_retrieval()
        self.aggregate_metrics()
