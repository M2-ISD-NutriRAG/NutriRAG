import pandas as pd
import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, TypedDict, Any
import pdb

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
        raw_data_cache_file_path: str,
        embedding_data_file_path: str,
        embedding_cache_file_path: str,
        data_columns: List[str],
        id_column: str,
        embedding_config: Dict[str, List[str]],
        embedding_model_list: List[str],
        override_raw_data: bool = False,
        override_embeddings: bool = False,
        number_row_analyse: int = 1000,
    ):
        self.client = client or SnowflakeClient()

        self.raw_data_table_name = raw_data_table_name
        self.number_row_analyse = number_row_analyse

        self.raw_data_file_path = raw_data_file_path
        self.raw_data_cache_file_path = raw_data_cache_file_path

        self.embedding_data_file_path = embedding_data_file_path
        self.embedding_cache_file_path = embedding_cache_file_path
        self.df_embedding_cache = (
            pd.read_csv(embedding_cache_file_path)
            if os.path.exists(embedding_cache_file_path)
            else pd.DataFrame()
        )

        self.data_columns = data_columns
        self.embedding_config = embedding_config
        self.id_column = id_column

        self.embedding_model_list = embedding_model_list

        self.override_raw_data = override_raw_data
        self.override_embeddings = override_embeddings

        self.df_recipes = pd.DataFrame()

    def get_raw_data(self):
        """Read raw data from the specified file path if it exists, otherwise fetch from Snowflake and save to file."""

        # check if the file already exists read it

        if (
            os.path.exists(self.raw_data_file_path)
            or os.path.exists(self.raw_data_cache_file_path)
        ) and not (self.override_raw_data):
            if os.path.exists(self.raw_data_file_path):
                print(
                    f"File {self.raw_data_file_path} already exists. Reading from file."
                )
                self.df_recipes = pd.read_csv(self.raw_data_file_path)
                return
            else:
                print(
                    f"File {self.raw_data_cache_file_path} exists. Reading from cache."
                )
                self.df_recipes = pd.read_csv(self.raw_data_cache_file_path)
                self.df_recipes.to_csv(self.raw_data_file_path, index=False)
                return

        pdb.set_trace()
        conn = self.client._conn

        columns_str = ", ".join([self.id_column] + self.data_columns)

        query = f"SELECT {columns_str} FROM {self.raw_data_table_name}"

        self.df_recipes = pd.read_sql(query, conn)

        self.client.close()

        # randomly sample number_row_analyse rows
        self.df_recipes = self.df_recipes.sample(
            n=self.number_row_analyse, random_state=42
        ).reset_index(drop=True)

        for col in self.data_columns:
            self.df_recipes[col] = self.df_recipes[col].apply(
                clean_columns_to_embedd, args=(f"recipe {col}",)
            )

        self.df_recipes.to_csv(self.raw_data_file_path, index=False)

    def create_embedding_combinaison_columns(self):
        """Create a columns for each combination of the columns to embed.
        example: NAME + INGREDIENTS, NAME + INGREDIENTS + DESCRIPTION, etc.
        """

        for col_config_name, cols_list in self.embedding_config.items():
            self.df_recipes[col_config_name] = ""

            for col in cols_list:
                self.df_recipes[col_config_name] += self.df_recipes[col] + " "

    def compute_embedding_columns(self):
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

        embedding_model_dict = load_embedding_models(self.embedding_model_list)

        for col_name, cols_list in tqdm(
            self.embedding_config.items(),
            desc="Computing embeddings for column combinations",
        ):
            for model_name, model in tqdm(
                embedding_model_dict.items(), desc="Computing embeddings for models"
            ):

                embedding_col = f"{model_name}/{col_name}_EMB"

                # Check if embeddings are already cached
                if (
                    embedding_col in self.df_embedding_cache.columns
                    and not (self.override_raw_data)
                    and not (self.override_embeddings)
                ):
                    print(f"Using cached embeddings for column {embedding_col}")
                    self.df_recipes[embedding_col] = self.df_embedding_cache[
                        embedding_col
                    ]
                    continue

                embeddings = compute_embedding(
                    model, self.df_recipes[col_name].astype(str).tolist()
                ).numpy()

                self.df_recipes[embedding_col] = list(embeddings)

                # add this embedding to the cache dataframe
                self.df_embedding_cache[embedding_col] = self.df_recipes[embedding_col]

        self.df_embedding_cache.to_csv(self.embedding_cache_file_path, index=False)

        if os.path.exists(self.embedding_data_file_path) and not (
            self.override_embeddings
        ):
            print(
                f"File {self.embedding_data_file_path} already exists. Skipping save."
            )
            return

        self.df_recipes.to_csv(self.embedding_data_file_path, index=False)
        print(f"Saving DataFrame to {self.embedding_data_file_path}")

    def main(self):
        """Main function to run the embedding calculation pipeline."""

        self.get_raw_data()
        self.create_embedding_combinaison_columns()
        self.compute_embedding_columns()
