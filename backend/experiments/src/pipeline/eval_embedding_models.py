import json
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Tuple, TypedDict, Any

from shared.snowflake.client import SnowflakeClient
from experiments.utils.llm import evaluate_documents_with_llm
from experiments.utils.calculate_embedding import (
    compute_embedding,
    load_embedding_models,
    retrieve_documents,
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
        override_documents_retrival: bool = False,
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
        self.retrived_model_query_docs_dict = {}

        self.override_documents_retrival = override_documents_retrival

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

    def retrive_documents_all_combinaison(self):
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

        for k in self.top_k:
            for emb_col in embeddings_cols:
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

    def main(self):
        """Main method to evaluate embedding models using LLM judge."""
        self.load_embeddings()
        self.retrive_documents_all_combinaison()
