import json
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Tuple, TypedDict, Any

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
        embedding_data_file_path: str,
        data_columns: List[str],
        eval_query_test_file_path: str,
        embedding_model_list: List[str],
        prompt_file_path: str,
        llm_model: str,
        llm_model_context_windows: int,
        llm_model_max_output_token: int,
        llm_model_temperature: float,
        json_schema: Dict[str, any],
        number_doc_per_call: int,
        max_retries_llm_calls: int,
        top_k: List[int],
        output_retrived_documents_file_path: str,
        output_retrived_query_documents_relevance_file: str,
        output_topk_model_query_retrieved_documents_relevance_file: str,
        output_retrived_documents_metrics_file_path: str,
        output_retrived_documents_aggregated_metrics_file_path: str,
        override_documents_retrival: bool = False,
        override_embedding_eval: bool = False,
    ):

        self.client = client

        self.df_recipes_embedding = pd.read_csv(embedding_data_file_path)

        self.data_columns = data_columns

        # Load the test queries
        with open(eval_query_test_file_path, "r", encoding="utf-8") as f:
            self.query_test = json.load(f)

        self.embedding_model_dict = load_embedding_models(embedding_model_list)

        # Load prompt template
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

        # model parameters
        self.llm_model = llm_model
        self.llm_model_context_windows = llm_model_context_windows
        self.llm_model_max_output_token = llm_model_max_output_token
        self.llm_model_temperature = llm_model_temperature
        self.max_retries_llm_calls = max_retries_llm_calls
        self.json_schema = json_schema
        self.number_doc_per_call = number_doc_per_call

        self.top_k = top_k

        self.output_retrived_documents_file_path = output_retrived_documents_file_path
        self.output_retrived_query_documents_relevance_file = (
            output_retrived_query_documents_relevance_file
        )
        self.output_topk_model_query_retrieved_documents_relevance_file = (
            output_topk_model_query_retrieved_documents_relevance_file
        )
        self.output_retrived_documents_metrics_file_path = (
            output_retrived_documents_metrics_file_path
        )
        self.output_retrived_documents_aggregated_metrics_file_path = (
            output_retrived_documents_aggregated_metrics_file_path
        )

        self.retrived_model_query_docs_dict = {}
        self.query_retrived_docs_dict = {}

        self.llm_results_dict = {}  # LLM relevance results

        self.retrived_model_query_docs_metrics_list = []  # metrics
        self.retrived_model_query_docs_metrics_agg_dict = {}

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
                for query in self.query_test:

                    # Convert embedding column to a list of numpy arrays
                    documents = (
                        self.df_recipes_embedding[emb_col].apply(np.array).to_list()
                    )

                    # Build model name + config name from column name
                    model_name = "/".join(emb_col.split("/")[:-1])
                    config_name = emb_col.split("/")[-1].replace("_EMB", "")

                    model = self.embedding_model_dict[model_name]

                    retrieved_documents_list = retrieve_documents(
                        query=query,
                        model=model,
                        documents=documents,
                        df=self.df_recipes_embedding,
                        columns_to_select=self.data_columns,
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
                            clean_doc = {col: doc[col] for col in self.data_columns}
                            doc_id = clean_doc["ID"]

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
            os.path.exists(self.output_retrived_query_documents_relevance_file)
            and not (self.override_documents_retrival)
            and not (self.override_embedding_eval)
        ):
            print(
                f"Loading cached results from {self.output_retrived_query_documents_relevance_file} ..."
            )
            with open(
                self.output_retrived_query_documents_relevance_file,
                "r",
                encoding="utf-8",
            ) as f:
                self.llm_results_dict = json.load(f)

            # Convert string keys back to integers
            self.llm_results_dict = {
                query: {int(doc_id): score for doc_id, score in doc_scores.items()}
                for query, doc_scores in self.llm_results_dict.items()
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
                doc_id = document["ID"]
                recipe_row = self.df_recipes_embedding[
                    self.df_recipes_embedding["ID"] == doc_id
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

                doc_entries.append({"ID": int(doc_id), "recipe_info": recipe_info})

            # Get relevance judgments from LLM
            relevance_judgments = evaluate_documents_with_llm(
                doc_entries=doc_entries,
                number_doc_per_call=self.number_doc_per_call,
                query_text=query,
                prompt_template=self.prompt_template,
                llm_model=self.llm_model,
                llm_model_temperature=self.llm_model_temperature,
                llm_model_max_output_token=self.llm_model_max_output_token,
                json_schema=self.json_schema,
                max_retries=self.max_retries_llm_calls,
            )

            self.llm_results_dict.setdefault(query, {})

            for doc in relevance_judgments:
                self.llm_results_dict[query][doc["ID"]] = float(
                    doc.get("relevance_score", 0.0)
                )

        with open(
            self.output_retrived_query_documents_relevance_file, "w", encoding="utf-8"
        ) as f:
            json.dump(self.llm_results_dict, f, indent=4)

    def map_documents_relevance_to_retrived_documents(self):
        """Map relevance scores back to the retrived documents."""

        for k, model_dict in self.retrived_model_query_docs_dict.items():
            for model_name, config_dict in model_dict.items():
                for config_name, query_dict in config_dict.items():
                    for query, docs in query_dict.items():

                        for doc in docs:
                            doc_id = doc.get("ID")

                            # attach relevance score if available
                            doc["relevance_score"] = self.llm_results_dict[query].get(
                                doc_id, 0.0
                            )

        with open(
            self.output_topk_model_query_retrieved_documents_relevance_file,
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

                        expected_retrived_docs = self.llm_results_dict[query_string]

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
        self.calculate_retrived_documents_relevance()
        self.map_documents_relevance_to_retrived_documents()

        self.evaluate_retrieval()
        self.aggregate_metrics()
