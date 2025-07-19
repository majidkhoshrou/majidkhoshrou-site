from pathlib import Path
from typing import List, Dict, Any
import json
import numpy as np
import faiss
from openai import OpenAI

def get_faiss_index(index_path: Path) -> faiss.Index:
    """
    Load a FAISS index from a given file path.

    Args:
        index_path (Path): Path to the FAISS index file.

    Returns:
        faiss.Index: The loaded FAISS index.
    """
    return faiss.read_index(str(index_path))

def load_chunks(chunks_path: Path) -> List[Dict[str, Any]]:
    """
    Load document chunks and their metadata from a JSON file.

    Args:
        chunks_path (Path): Path to the JSON file containing chunks.

    Returns:
        List[Dict[str, Any]]: A list of chunk dictionaries.
    """
    with chunks_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def query_index(
    query: str,
    index: faiss.Index,
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Embed the query and return the top-k most relevant chunks.

    Args:
        query (str): The user's question.
        index (faiss.Index): The FAISS index to search.
        chunks (List[Dict[str, Any]]): List of all document chunks with metadata.
        top_k (int, optional): Number of top matches to return. Defaults to 5.

    Returns:
        List[Dict[str, Any]]: Top-matching chunks with source and text info.
    """
    client = OpenAI()
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    embedding = np.array(response.data[0].embedding).astype("float32").reshape(1, -1)
    distances, indices = index.search(embedding, top_k)
    return [chunks[i] for i in indices[0] if i < len(chunks)]
