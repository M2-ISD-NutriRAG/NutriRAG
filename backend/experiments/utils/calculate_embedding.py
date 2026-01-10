import pandas as pd
import numpy as np
import pdb

from typing import List, Dict, Tuple, TypedDict, Any

import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from torch.nn.functional import normalize
from sentence_transformers import SentenceTransformer


def load_embedding_models(
    embedding_model_list: list[str],
) -> dict[str, SentenceTransformer]:
    """load the different embedding models"""

    model_list = [
        SentenceTransformer(model_id)
        for model_id in tqdm(embedding_model_list, desc="Loading embedding models")
    ]
    return dict(zip(embedding_model_list, model_list))


def compute_embedding(
    model: SentenceTransformer, text_list: list[str], batch_size: int = 256
) -> torch.Tensor:
    """
    Compute normalized embeddings for a list of texts using the specified model.

    Args:
        model (SentenceTransformer): The pre-trained sentence transformer model to use.
        texts_list (list[str]): A list of input texts to compute embeddings for.
        batch_size (int): The number of texts to process in each batch.

    Returns:
        torch.Tensor: A tensor containing the normalized embeddings for the input texts.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)

    embeddings = []

    for i in tqdm(
        range(0, len(text_list), batch_size), desc="Computing embeddings chunks"
    ):
        batch_texts = text_list[i : i + batch_size]
        batch_embeddings = model.encode(
            batch_texts,
            convert_to_tensor=True,
            device=device,
            normalize_embeddings=True,
        ).cpu()
        embeddings.append(batch_embeddings)

    return torch.cat(embeddings, dim=0)


def retrieve_documents(
    query: str,
    model: SentenceTransformer,
    documents: List[Any],
    df: pd.DataFrame,
    columns_to_select: List[str],
    top_k: int,
) -> Dict[str, Any]:
    """
    Retrieve top-k documents relevant to the query using the specified embedding model.

    Returns:
        list: [{col1: ..., col2: ..., similarity_score: ...}, ...]
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)

    # Generate query embedding
    query_embedding = model.encode(
        [query], convert_to_tensor=True, device=device, normalize_embeddings=True
    )

    # Build document embedding tensor
    document_embeddings = torch.tensor(
        np.array(documents), dtype=torch.float32, device=device
    )

    # Compute cosine similarity
    cosine_scores = torch.matmul(query_embedding, document_embeddings.T).squeeze(0)

    # Top-k results
    top_k_results = torch.topk(cosine_scores, k=top_k)
    top_k_indices = top_k_results.indices.tolist()
    top_k_scores = top_k_results.values.tolist()

    # Select rows & columns
    retrieved_df = df.iloc[top_k_indices][columns_to_select].copy()

    # Add similarity scores
    retrieved_df["similarity_score"] = top_k_scores

    # Return list of documents
    return retrieved_df.to_dict(orient="records")
