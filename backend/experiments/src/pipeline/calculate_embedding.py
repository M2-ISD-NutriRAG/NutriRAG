import pandas as pd
import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, TypedDict, Any

from shared.snowflake.client import SnowflakeClient
from experiments.utils.clean_text import clean_columns_to_embedd
from experiments.utils.calculate_embedding import (
    compute_embedding,
    load_embedding_models,
)


class CalculateEmbedding:
    def __init__(
        self,
        client: SnowflakeClient,
        raw_data_table_name: str,
        raw_data_file_path: str,
        embedding_data_file_path: str,
        embedding_cache_file_path: str,
        data_columns_for_embedding: Dict[str, Dict[str, str]],
        embedding_configuration: Dict[str, List[str]],
        embedding_model_list: List[str],
        override_raw_data: bool = False,
        override_embeddings: bool = False,
    ):
        self.client = client

        self.raw_data_table_name = raw_data_table_name

        self.raw_data_file_path = raw_data_file_path
        self.embedding_data_file_path = embedding_data_file_path

        self.df_recipes = pd.DataFrame()
        self.df_recipes_cleaned = pd.DataFrame()
        self.df_recipes_embedding = pd.DataFrame()

        self.df_embedding_cache = (
            pd.read_csv(embedding_cache_file_path)
            if os.path.exists(embedding_cache_file_path)
            else pd.DataFrame()
        )

        self.data_columns_for_embedding = data_columns_for_embedding
        self.embedding_configuration = embedding_configuration

        self.embedding_model_dict = load_embedding_models(embedding_model_list)

        self.override_raw_data = override_raw_data
        self.override_embeddings = override_embeddings

    def get_raw_data(self):
        """Read raw data from the specified file path."""

        self.df_recipes = pd.DataFrame()

        # check if the file already exists read it
        if os.path.exists(self.raw_data_file_path) and not (self.override_raw_data):
            print(f"File {self.raw_data_file_path} already exists. Skipping save.")
            self.df_recipes = pd.read_csv(self.raw_data_file_path)
        else:
            print(f"Saving DataFrame to {self.raw_data_file_path}")
            self.client = SnowflakeClient()

            conn = self.client._conn

            self.df_recipes = pd.read_sql(
                f"SELECT * FROM {self.raw_data_table_name}", conn
            )

            self.client.close()

            self.df_recipes.to_csv(self.raw_data_file_path, index=False)

    def extract_required_columns_for_embedding(self):
        """Extract and clean required columns for embedding."""

        for col in self.data_columns_for_embedding:
            col_clean_name = self.data_columns_for_embedding[col]["column_name"]
            start_text = self.data_columns_for_embedding[col]["start_text"]

            self.df_recipes_cleaned[col_clean_name] = self.df_recipes[col].apply(
                clean_columns_to_embedd, args=(start_text,)
            )

        self.df_recipes_cleaned["ID"] = self.df_recipes["ID"]

    def create_embedding_combinaison_columns(self):
        """Create a columns for each combination of the columns to embed.
        example: NAME + INGREDIENTS, NAME + INGREDIENTS + DESCRIPTION, etc.
        """

        for col_config_name, cols_list in self.embedding_configuration.items():
            self.df_recipes_cleaned[col_config_name] = ""

            for col in cols_list:
                column_name_cleaned = self.data_columns_for_embedding[col][
                    "column_name"
                ]
                self.df_recipes_cleaned[col_config_name] += (
                    self.df_recipes_cleaned[f"{column_name_cleaned}"] + " "
                )

    def compute_embedding(self):
        """compute embedding for each combination of columns and each embedding model"""

        # if the embedding file already exists, skip the computation
        if os.path.exists(self.embedding_data_file_path) and not (
            self.override_embeddings
        ):
            print(
                f"File {self.embedding_data_file_path} already exists. Skipping embedding computation."
            )
            self.df_recipes_embedding = pd.read_csv(self.embedding_data_file_path)
            return

        self.df_recipes_embedding = self.df_recipes_cleaned.copy()

        for col_name, cols_list in self.embedding_configuration.items():
            for model_id, model in self.embedding_model_dict.items():

                embedding_col = f"{model_id}/{col_name}_EMB"

                # Check if embeddings are already cached
                if (
                    embedding_col in self.df_embedding_cache.columns
                    and not (self.override_raw_data)
                    and not (self.override_embeddings)
                ):
                    print(f"Using cached embeddings for column {embedding_col}")
                    self.df_recipes_embedding[embedding_col] = self.df_embedding_cache[
                        embedding_col
                    ]
                    continue

                embeddings = []
                for text in tqdm(
                    self.df_recipes_embedding[col_name],
                    desc=f"Embedding {col_name} with {model_id}",
                ):
                    emb = compute_embedding(model, [text])[0].numpy()
                    embeddings.append(emb)

                self.df_recipes_embedding[embedding_col] = embeddings

                # add this embedding to the cache dataframe
                self.df_embedding_cache[embedding_col] = self.df_recipes_embedding[
                    embedding_col
                ]

        # Save the updated cache dataframe
        self.df_embedding_cache.to_csv(self.embedding_cache_file_path, index=False)

    def main(self):
        """Main function to run the embedding calculation pipeline."""

        self.get_raw_data()
        self.extract_required_columns_for_embedding()
        self.create_embedding_combinaison_columns()
        # self.compute_embedding()

        if os.path.exists(self.embedding_data_file_path) and not (
            self.override_embeddings
        ):
            print(
                f"File {self.embedding_data_file_path} already exists. Skipping save."
            )
            return

        print(f"Saving DataFrame to {self.embedding_data_file_path}")
        self.df_recipes_embedding.to_csv(self.embedding_data_file_path, index=False)
